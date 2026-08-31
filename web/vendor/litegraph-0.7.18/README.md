# LiteGraph 0.7.18 vendor record

This directory contains the exact browser assets used by the local
`skill2workflow` visual editor. They are committed so `skill2workflow ui` and
the static preview do not require a CDN, internet egress, or a package-manager
install at runtime.

- Upstream package: `litegraph.js` 0.7.18
- Source: `https://cdn.jsdelivr.net/npm/litegraph.js@0.7.18/`
- License: MIT; the complete upstream notice is in [`LICENSE`](LICENSE)
- Files intentionally included: `build/litegraph.min.js` and
  `css/litegraph.css`

SHA-256 digests of the downloaded upstream files:

```text
6a6bd1480057107b8dc12b40730b88afb01729ebcbf0555cd67f5a229f381589  litegraph.min.js
565cee8d54e7dfd16295f0ec7b19f910a739c0f42d5263198e3416a38a6006b3  litegraph.css
8bc224b3d4a8e3a7729f57bc7f4eb35f3946d6b476edbf9e725c551dd7f6d72b  LICENSE
```

Do not replace these files with an unpinned CDN URL. To upgrade LiteGraph,
review the upstream license and changelog, update all three assets together,
refresh the digests above, and extend the editor asset-integrity test.
