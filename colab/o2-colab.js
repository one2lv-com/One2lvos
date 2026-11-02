/* One2lvOS Colab add-on for one2lvos-desktop.html.
 * The Colab gateway injects this into /desktop. It adds:
 *  - Ubuntu 26 Terminal: a real shell (ttyd) in the notebook's Ubuntu 26 root, at /terminal/
 *  - Lumenis Console: the full static/lumenis-chat.html UI as a window (its terminal also runs in Ubuntu 26)
 * The desktop's own built-in "Lumenis Chat" app keeps working: it talks to the reactor over /ws.
 * Terminal, Lumenis Chat and Lumenis Console are moved to the front of the icon grid.
 */
(function () {
    if (typeof apps === 'undefined') return;
    const frame = (id, src, bg) => `<div class="h-full flex flex-col" style="background:${bg}">
        <iframe src="${src}" id="${id}" class="flex-1 w-full border-none" style="background:${bg}"
                allow="clipboard-read; clipboard-write"></iframe>
        <div class="text-[10px] text-gray-400 px-3 py-1 flex justify-between" style="background:#0b0b12">
          <span>${src}</span>
          <span>
            <button onclick="document.getElementById('${id}').src='${src}'" class="hover:text-white mr-3"><i class="fas fa-redo-alt"></i> Reload</button>
            <button onclick="window.open('${src}','_blank')" class="hover:text-white"><i class="fas fa-external-link-alt"></i> New tab</button>
          </span>
        </div></div>`;

    const added = {
        'ubuntu-terminal': {
            name: 'Ubuntu 26 Terminal', icon: 'fab fa-ubuntu', color: 'text-orange-500',
            width: 920, height: 560,
            content: frame('o2-ttyd-frame', '/terminal/', '#000'),
            onOpen: () => setTimeout(() => { const f = document.getElementById('o2-ttyd-frame'); if (f) f.focus(); }, 400),
        },
        'lumenis-console': {
            name: 'Lumenis Console', icon: 'fas fa-atom', color: 'text-cyan-300',
            width: 1060, height: 720,
            content: frame('o2-lumenis-frame', '/lumenis-chat', '#07030f'),
        },
    };

    // Rebuild the apps table with the Colab apps first (apps is a const object: mutate in place).
    const front = ['ubuntu-terminal', 'lumenis-chat', 'lumenis-console'];
    const rest = Object.keys(apps).filter(k => !front.includes(k));
    const saved = Object.assign({}, apps);
    Object.keys(apps).forEach(k => delete apps[k]);
    front.forEach(k => { const a = added[k] || saved[k]; if (a) apps[k] = a; });
    rest.forEach(k => { apps[k] = saved[k]; });

    // About box: say where this desktop is running.
    if (apps.about) {
        apps.about.content = apps.about.content.replace(
            /Hosted: <span[^>]*>[^<]*<\/span>/,
            'Hosted: <span class="text-blue-600 font-mono">Google Colab (Ubuntu 26 root)</span>');
    }

    // Open the terminal next to the About box once the desktop has drawn its icons.
    window.addEventListener('load', () => setTimeout(() => {
        try { openApp('ubuntu-terminal'); } catch (e) { console.warn('o2-colab', e); }
    }, 1200));
    window.O2_COLAB = { apps: Object.keys(added) };
})();
