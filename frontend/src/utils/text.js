// text.js — display-layer copy cleanup for text that comes from the backends
// (Person 1's analysis reasoning, Person 2's suggestion reasoning, etc.), which
// we don't own and can't guarantee stays em-dash-free at the source. Anywhere a
// dynamic reasoning/note/label string from a report is rendered, run it through
// stripLongDashes() so the site's "no em-dashes" rule holds everywhere, not just
// in our own static copy.
export function stripLongDashes(text) {
  if (typeof text !== "string") return text;
  return text
    .replace(/\s*[—–]\s*/g, ", ")
    .replace(/,\s*,/g, ",")
    .replace(/\s+/g, " ")
    .trim();
}
