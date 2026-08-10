// Receives client intake form submissions from /intake.
// Browser uploads files directly to Vercel Blob first (see /api/intake-upload-token),
// then POSTs the form here with Blob URLs. This handler:
//   1. Appends a row to the lead sheet via Apps Script doPost — first, so a lead
//      is recorded even if the email leg fails
//   2. Downloads each blob, attaches it to a Resend email to David
//   3. Deletes the blobs, but ONLY once the email is accepted — the email is the
//      persistence layer for attachments, so a failed send must keep them

import { del } from '@vercel/blob';

function cleanEnv(v) { return (v || '').replace(/\\n/g, '').replace(/\n/g, '').trim(); }

const RESEND_API_KEY = cleanEnv(process.env.RESEND_API_KEY);
const LEADS_SHEET_URL = cleanEnv(process.env.LEADS_SHEET_URL);
const LEADS_SHEET_TOKEN = cleanEnv(process.env.LEADS_SHEET_TOKEN);
const BLOB_TOKEN = cleanEnv(process.env.BLOB_READ_WRITE_TOKEN);
const NOTIFY_EMAIL = 'davidvd@shieldagency.com';
const FROM_EMAIL = 'Shield Insurance Intake <leads@davidvandykeinsurance.com>';
const MAX_EMAIL_BYTES = 22 * 1024 * 1024; // ~22 MB attachments total — keeps email under Gmail's 25 MB cap

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { answers, files, summary, clientName } = req.body || {};
    if (!answers || typeof answers !== 'object') {
      return res.status(400).json({ error: 'Missing answers payload' });
    }

    // files: [{ name, url, type, size }]
    const blobs = Array.isArray(files) ? files.filter(f => f && f.url) : [];

    // Server-side size guard
    const totalBytes = blobs.reduce((s, f) => s + (Number(f.size) || 0), 0);
    if (totalBytes > MAX_EMAIL_BYTES) {
      // Best-effort cleanup of orphaned blobs before erroring
      await cleanupBlobs(blobs);
      return res.status(413).json({
        error: `Attachments total ${(totalBytes / 1024 / 1024).toFixed(1)} MB exceeds 22 MB email limit. Please reduce file sizes.`,
      });
    }

    // Fetch each blob and encode as base64 for Resend
    const attachments = [];
    for (const f of blobs) {
      try {
        const r = await fetch(f.url);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const buf = Buffer.from(await r.arrayBuffer());
        attachments.push({ filename: f.name || 'attachment', content: buf.toString('base64') });
      } catch (e) {
        console.error(`Failed to fetch blob ${f.url}:`, e.message);
        // Continue with other files rather than failing the whole submission
      }
    }

    const html = renderEmail({ answers, summary, clientName, fileCount: attachments.length });
    const replyTo = guessReplyTo(answers);
    const subject = `📋 Intake form: ${clientName || 'New client'}${answers.policy_type ? ' — ' + answers.policy_type : ''}`;

    // 1. Append to the leads sheet first, so the lead survives an email failure
    //    and still shows up on the dashboard.
    try {
      const leadId = `intake_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const sheetUrl = `${LEADS_SHEET_URL}?token=${encodeURIComponent(LEADS_SHEET_TOKEN)}`;
      await fetch(sheetUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'append',
          id: leadId,
          name: clientName || guessName(answers),
          phone: guessPhone(answers),
          email: guessEmail(answers),
          type: answers.policy_type || '',
          created_at: new Date().toISOString(),
          campaign_name: 'Website Intake Form',
          adset_name: 'Intake',
          ad_name: 'Intake form submission',
        }),
        redirect: 'manual',
      });
    } catch (sheetErr) {
      console.warn('Sheet append failed (non-fatal):', sheetErr.message);
    }

    // 2. Send the email
    const emailResp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: FROM_EMAIL,
        to: [NOTIFY_EMAIL],
        ...(replyTo ? { reply_to: replyTo } : {}),
        subject,
        html,
        attachments,
      }),
    });
    if (!emailResp.ok) {
      // Do NOT swallow this. The lead is already in the sheet, but David won't be
      // notified, so say so instead of rendering an unqualified success screen.
      // Blobs are deliberately left in place — without a sent email they are the
      // only remaining copy of the client's documents.
      const err = await emailResp.text();
      console.error(
        `Resend error: HTTP ${emailResp.status} from ${FROM_EMAIL} → ${NOTIFY_EMAIL}: ${err || '(empty response body)'}`
      );
      if (blobs.length) {
        console.error('Retained blobs (email failed):', blobs.map(f => f.url).join(', '));
      }
      return res.status(200).json({
        success: true,
        emailDelivered: false,
        emailError: `Resend rejected the send (HTTP ${emailResp.status}).`,
      });
    }

    // 3. Delete blobs — the email is now the persistence layer
    await cleanupBlobs(blobs);

    return res.status(200).json({ success: true, emailDelivered: true });
  } catch (err) {
    console.error('Intake submit error:', err);
    return res.status(500).json({ error: err.message || 'Internal error' });
  }
}

async function cleanupBlobs(blobs) {
  await Promise.allSettled(
    (blobs || []).map(f => f?.url ? del(f.url, { token: BLOB_TOKEN }) : null)
  );
}

function guessReplyTo(answers) {
  for (const v of Object.values(answers || {})) {
    if (typeof v === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())) return v.trim();
  }
  return null;
}

function guessName(answers) {
  if (answers.applicant_people) {
    try {
      const people = JSON.parse(answers.applicant_people);
      if (Array.isArray(people) && people.length) {
        return people.map(p => `${p.first || ''} ${p.last || ''}`.trim()).filter(Boolean).join(' & ');
      }
    } catch (_) {}
  }
  return '';
}

function guessPhone(answers) {
  for (const [k, v] of Object.entries(answers || {})) {
    if (typeof v === 'string' && /phone/i.test(k) && v.trim()) return v.trim();
  }
  for (const v of Object.values(answers || {})) {
    if (typeof v === 'string' && /^[\d\s().+-]{10,}$/.test(v.trim())) return v.trim();
  }
  return '';
}

function guessEmail(answers) { return guessReplyTo(answers) || ''; }

function escape(s) {
  return String(s ?? '').replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
}

function renderEmail({ answers, summary, clientName, fileCount }) {
  const summaryHtml = `<pre style="font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;background:#f7fafc;padding:16px;border-radius:6px;border:1px solid #e2e8f0;white-space:pre-wrap;word-break:break-word;margin:0">${escape(summary || JSON.stringify(answers, null, 2))}</pre>`;
  return `
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:720px;margin:0 auto;padding:24px;background:#f7fafc">
      <div style="background:#1a365d;color:white;padding:24px;border-radius:8px 8px 0 0">
        <h1 style="margin:0;font-size:22px">📋 New Client Intake Form</h1>
        <p style="margin:6px 0 0;opacity:0.85;font-size:14px">From ${escape(clientName || 'a prospective client')} — high-intent lead, completed the full intake</p>
      </div>
      <div style="background:white;padding:24px;border-radius:0 0 8px 8px;border:1px solid #e2e8f0;border-top:none">
        ${fileCount ? `<div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:12px 14px;border-radius:6px;margin-bottom:16px;color:#065f46;font-size:14px">📎 <strong>${fileCount} document${fileCount === 1 ? '' : 's'} attached</strong> to this email — check your attachments.</div>` : ''}
        ${summaryHtml}
        <div style="margin-top:24px;padding:14px;background:#fffbeb;border:1px solid #f6e05e;border-radius:6px">
          <p style="margin:0;color:#744210;font-size:14px">
            ⚡ <strong>High-intent lead</strong> — this person filled out the full intake form. Reply directly to this email to respond.
          </p>
        </div>
      </div>
    </div>
  `;
}
