// Returns a Vercel Blob client-upload token so the browser can upload intake form
// attachments directly to Blob storage, bypassing Vercel's 4.5 MB function body limit.
//
// Flow:
//   1. Browser POSTs { filename, contentType } via the @vercel/blob/client helper
//   2. This handler validates and returns a short-lived signed upload URL
//   3. Browser PUTs the file bytes to that URL (bytes never touch our serverless)
//   4. Browser then submits the form with the resulting Blob URLs
//   5. /api/intake-submit downloads them, attaches to email, and deletes them

import { handleUpload } from '@vercel/blob/client';

const ALLOWED_TYPES = new Set([
  'application/pdf',
  'image/jpeg', 'image/png', 'image/gif', 'image/heic', 'image/heif', 'image/webp',
]);
const MAX_FILE_BYTES = 15 * 1024 * 1024; // 15 MB per file — fits within Gmail's 25 MB inbound

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const body = req.body;
    const result = await handleUpload({
      body,
      request: req,
      onBeforeGenerateToken: async (pathname, clientPayload) => {
        // pathname is the proposed object key. We don't need to inspect clientPayload here;
        // we just constrain allowed types and sizes via the token itself.
        return {
          allowedContentTypes: [...ALLOWED_TYPES],
          maximumSizeInBytes: MAX_FILE_BYTES,
          // 30-minute upload window. After upload, /api/intake-submit deletes the blob anyway.
          tokenPayload: JSON.stringify({ source: 'intake', pathname }),
          addRandomSuffix: true,
        };
      },
      onUploadCompleted: async ({ blob }) => {
        // No-op. We don't need to do anything on successful upload — the browser
        // will hand the blob URL back to /api/intake-submit which handles cleanup.
        console.log('Intake blob uploaded:', blob.pathname);
      },
    });
    return res.status(200).json(result);
  } catch (err) {
    console.error('intake-upload-token error:', err);
    return res.status(400).json({ error: err.message || 'Token generation failed' });
  }
}
