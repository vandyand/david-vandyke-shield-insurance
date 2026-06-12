// Scrape Grace Fellowship's Instant Church Directory into a CSV.
//
// USAGE:
//   1. Log in to https://members.instantchurchdirectory.com and navigate to /families/{dirId}
//      (the page that shows the family list in the left sidebar).
//   2. Open DevTools -> Console (F12).
//   3. Paste THIS WHOLE FILE and hit Enter. Wait ~30-60 sec.
//   4. A CSV file will auto-download. Save / move as needed.
//
// CSV columns: Family Name | Adults | Kids | All Members | Greeting (envelope-ready)
//              | Street | City State Zip | Emails | Phones
//
// Emails and phones are formatted "Person: value; Person: value" when the directory
// labels them; otherwise just the value. Asterisks marking app-account holders are
// stripped. Greeting is envelope-ready ("Dave and Sheryl Alkema").

(async () => {
  const dirId = (location.pathname.match(/\/famil(?:y|ies)\/([0-9a-f-]{36})/) || [])[1]
            || (document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('icd-members-directory-id=')) || '').split('=')[1];
  if (!dirId) return alert('Could not find directory ID. Open /families/{dirId} first.');

  const familyIds = [...new Set([...document.querySelectorAll('[data-family-id]')].map(el => el.dataset.familyId))];
  if (!familyIds.length) return alert('No families in DOM. Open /families/{dirId} first.');
  console.log(`Scraping ${familyIds.length} families…`);

  const stripStars = s => (s || '').replace(/\*/g, '').trim();
  const cleanText = s => (s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').replace(/^[,\s]+|[,\s]+$/g, '').trim();

  // Dedupe by value, prefer a non-empty label if one exists for the value
  const formatLabeled = arr => {
    const map = new Map();
    for (const { value, label } of arr) {
      if (!value) continue;
      if (!map.has(value) || (label && !map.get(value))) map.set(value, label);
    }
    return [...map.entries()].map(([v, l]) => l ? `${l}: ${v}` : v).join('; ');
  };

  function parseFamily(html, id) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const detailH3 = [...doc.querySelectorAll('h3')].find(h =>
      !h.querySelector('i') && h.textContent.trim() &&
      !/^\s*(Families|Staff|Groups|Account|About|Church|Additional Pages)\s*$/i.test(h.textContent)
    );
    const familyName = stripStars(detailH3?.textContent);

    const memberP = detailH3?.parentElement?.querySelector('p');
    let adultsText = '', kidsText = '', allMembersText = '';
    if (memberP) {
      const segs = memberP.innerHTML.split(/<br\s*\/?>/i);
      adultsText = stripStars(cleanText(segs[0]));
      kidsText = stripStars(cleanText(segs.slice(1).join(', ')));
      allMembersText = [adultsText, kidsText].filter(Boolean).join(', ');
    }
    const adultsList = adultsText.split(/\s+and\s+|,\s*/).map(s => s.trim()).filter(Boolean);
    const greeting = (adultsList.length ? `${adultsList.join(' and ')} ${familyName}` : familyName).trim();

    let street = '', cityStateZip = '', emails = [], phones = [];
    for (const row of doc.querySelectorAll('div.row')) {
      const icon = row.querySelector('i.fa, i[class*="fa-"]');
      if (!icon) continue;
      const cols = row.querySelectorAll(':scope > div');
      const dataCol = cols[cols.length - 1];
      if (!dataCol) continue;
      const cls = icon.className;

      if (cls.includes('fa-map-marker')) {
        const parts = dataCol.innerHTML.split(/<br\s*\/?>/i).map(cleanText).filter(Boolean);
        street = parts[0] || '';
        cityStateZip = parts.slice(1).join(', ');
      } else if (cls.includes('fa-envelope')) {
        const link = dataCol.querySelector('a[href^="mailto:"]');
        if (link) {
          const small = dataCol.querySelector('small');
          const label = small ? stripStars(small.textContent) : '';
          emails.push({ value: link.textContent.trim(), label });
        }
      } else if (cls.includes('fa-phone')) {
        const small = dataCol.querySelector('small');
        const label = small ? stripStars(small.textContent) : '';
        const cloned = dataCol.cloneNode(true);
        cloned.querySelectorAll('small, br, a').forEach(n => n.remove());
        const value = cloned.textContent.replace(/\s+/g, ' ').trim();
        if (value) phones.push({ value, label });
      }
    }
    return {
      familyId: id, familyName, adults: adultsText, kids: kidsText,
      allMembers: allMembersText, greeting, street, cityStateZip,
      emails: formatLabeled(emails), phones: formatLabeled(phones),
    };
  }

  const results = [];
  let done = 0;
  const queue = [...familyIds];
  await Promise.all(Array.from({ length: 5 }, async () => {
    while (queue.length) {
      const id = queue.shift();
      try {
        const r = await fetch(`/family/${dirId}/${id}`, { credentials: 'include' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        results.push(parseFamily(await r.text(), id));
      } catch (e) {
        results.push({ familyId: id, error: e.message });
      }
      done++;
      if (done % 20 === 0 || done === familyIds.length) console.log(`  ${done}/${familyIds.length}`);
    }
  }));
  results.sort((a, b) => (a.familyName || '').localeCompare(b.familyName || ''));

  // CSV — use commaless header names so a downstream parser doesn't get confused
  const headers = ['Family Name', 'Adults', 'Kids', 'All Members', 'Greeting (envelope-ready)',
                   'Street', 'City State Zip', 'Emails', 'Phones'];
  const esc = v => { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const csv = [headers.join(','), ...results.map(r =>
    [r.familyName, r.adults, r.kids, r.allMembers, r.greeting,
     r.street, r.cityStateZip, r.emails, r.phones].map(esc).join(',')
  )].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `church-directory-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a); a.click(); a.remove();

  const haveAddr = results.filter(r => r.street).length;
  console.log(`Done. ${results.length} families · ${haveAddr} with mailing address. CSV downloaded.`);
  window.__icdScrapeResults = results;
})();
