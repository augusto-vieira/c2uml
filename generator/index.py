import os


def generate_index_html(out_dir, module_names, has_svg, has_png, packages=None, include_deps=None):
    ext = "svg" if has_svg else "png"
    include_deps = include_deps or []

    dep_count = {}
    for src, dst in include_deps:
        if src and dst and src != dst:
            dep_count[src] = dep_count.get(src, 0) + 1

    class_names = {}
    if packages:
        for name in module_names:
            if name in packages:
                pkg = packages[name]
                names = [s.name for s in pkg.get("structs", [])]
                names += [e.name for e in pkg.get("enums", [])]
                names += [cb.name for cb in pkg.get("callbacks", [])]
                class_names[name] = names

    cards = []
    for name in sorted(module_names):
        n_structs = n_enums = n_callbacks = n_methods = n_unions = 0
        if packages and name in packages:
            pkg = packages[name]
            for s in pkg.get("structs", []):
                if s.stereotype == "union":
                    n_unions += 1
                else:
                    n_structs += 1
                n_methods += len(s.methods)
            n_enums = len(pkg.get("enums", []))
            n_callbacks = len(pkg.get("callbacks", []))
        n_deps = dep_count.get(name, 0)
        cards.append((name, n_structs, n_enums, n_callbacks, n_methods, n_deps, n_unions))

    total_structs = sum(c[1] for c in cards)
    total_methods = sum(c[4] for c in cards)
    total_enums = sum(c[2] for c in cards)

    lines = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html><head>')
    lines.append('<meta charset="utf-8">')
    lines.append('<title>c2uml</title>')
    lines.append('<style>')
    lines.append("""
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }

.header { padding: 2em 2.5em 1.5em; }
.header h1 { color: #f1f5f9; font-size: 1.6em; font-weight: 700; }
.header h1 span { color: #38bdf8; }
.stats { display: flex; gap: 1.5em; margin-top: 0.6em; }
.stat { font-size: 0.85em; color: #64748b; }
.stat b { color: #38bdf8; font-size: 1.1em; }

.search-bar {
  margin: 0 2.5em 1.5em; display: flex; align-items: center; gap: 0;
}
.search-bar input {
  flex: 1; max-width: 400px; padding: 0.6em 1em; background: #1e293b; border: 1px solid #334155;
  border-radius: 8px 0 0 8px; color: #e2e8f0; font-size: 0.9em; outline: none;
}
.search-bar input:focus { border-color: #0ea5e9; }
.search-tabs { display: flex; }
.search-tabs button {
  padding: 0.6em 1em; border: 1px solid #334155; border-left: none; background: #1e293b;
  color: #64748b; cursor: pointer; font-size: 0.82em; transition: all 0.15s;
}
.search-tabs button:last-child { border-radius: 0 8px 8px 0; }
.search-tabs button.active { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }
.search-tabs button:hover:not(.active) { background: #334155; color: #cbd5e1; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1em; padding: 0 2.5em 2em; }

.card {
  background: #1e293b; border: 1px solid #334155; border-radius: 10px;
  padding: 1.2em; transition: all 0.2s; cursor: pointer; text-decoration: none; display: block;
}
.card:hover { border-color: #0ea5e9; box-shadow: 0 4px 20px rgba(14,165,233,0.1); transform: translateY(-2px); }
.card-name { color: #38bdf8; font-weight: 600; font-size: 1em; margin-bottom: 0.6em; }
.card-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 0.3em 1em; }
.card-metric { font-size: 0.78em; color: #64748b; display: flex; align-items: center; gap: 0.3em; }
.card-metric b { color: #cbd5e1; }
.card-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-class { background: #fbbf24; }
.dot-enum { background: #f87171; }
.dot-cb { background: #a78bfa; }
.dot-method { background: #34d399; }
.dot-dep { background: #38bdf8; }
.dot-union { background: #6ee7b7; }
""")
    lines.append('</style>')
    lines.append('</head><body>')
    lines.append('<div class="header">')
    lines.append(f'  <h1><span>c2uml</span> &mdash; {len(module_names)} modules</h1>')
    lines.append(f'  <div class="stats">')
    lines.append(f'    <span class="stat"><b>{total_structs}</b> classes</span>')
    lines.append(f'    <span class="stat"><b>{total_enums}</b> enums</span>')
    lines.append(f'    <span class="stat"><b>{total_methods}</b> methods</span>')
    lines.append(f'  </div>')
    lines.append('</div>')
    lines.append('<div class="search-bar">')
    lines.append('  <input type="text" id="filter" placeholder="Search modules..." oninput="filterCards()">')
    lines.append('  <div class="search-tabs">')
    lines.append('    <button class="active" onclick="setMode(\'module\',this)">modules</button>')
    lines.append('    <button onclick="setMode(\'class\',this)">classes</button>')
    lines.append('  </div>')
    lines.append('</div>')
    lines.append('<div class="grid" id="grid">')

    for name, ns, ne, nc, nm, nd, nu in cards:
        cls_data = ','.join(c.lower() for c in class_names.get(name, []))
        link = f"{name}.html" if has_svg else f"{name}.{ext}"
        lines.append(f'  <a class="card" href="{link}" data-name="{name}" data-classes="{cls_data}">')
        lines.append(f'    <div class="card-name">{name}</div>')
        lines.append(f'    <div class="card-metrics">')
        lines.append(f'      <span class="card-metric"><span class="card-dot dot-class"></span> <b>{ns}</b> classes</span>')
        lines.append(f'      <span class="card-metric"><span class="card-dot dot-enum"></span> <b>{ne}</b> enums</span>')
        lines.append(f'      <span class="card-metric"><span class="card-dot dot-cb"></span> <b>{nc}</b> callbacks</span>')
        lines.append(f'      <span class="card-metric"><span class="card-dot dot-union"></span> <b>{nu}</b> unions</span>')
        lines.append(f'      <span class="card-metric"><span class="card-dot dot-method"></span> <b>{nm}</b> methods</span>')
        lines.append(f'      <span class="card-metric"><span class="card-dot dot-dep"></span> <b>{nd}</b> deps</span>')
        lines.append(f'    </div>')
        lines.append(f'  </a>')

    lines.append('</div>')
    lines.append('<script>')
    lines.append("""
let searchMode = 'module';
function setMode(mode, btn) {
  searchMode = mode;
  document.querySelectorAll('.search-tabs button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('filter').placeholder = mode === 'module' ? 'Search modules...' : 'Search classes...';
  filterCards();
}
function filterCards() {
  const q = document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('.card').forEach(c => {
    if (searchMode === 'module') {
      c.style.display = c.dataset.name.includes(q) ? '' : 'none';
    } else {
      c.style.display = (c.dataset.classes || '').includes(q) ? '' : 'none';
    }
  });
}
""")
    lines.append('</script>')
    lines.append('</body></html>')

    path = os.path.join(out_dir, "index.html")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path
