// Single-line field behavior from the prototype: clicking or focusing a field
// selects its content (quick overwrite), and Enter leaves the field.
export const vField = {
  mounted(el) {
    el.addEventListener('click', () => el.select())
    el.addEventListener('focus', () => el.select())
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault()
        el.blur()
      }
    })
  },
}

// The right column of a detail page (vulnerability, report) scrolls on its own: it stays in
// view under the sticky page header, as tall as the room left, while the left column scrolls
// the page. One column (narrow screens) or a short column: nothing changes.
const WIDE = '(min-width: 1101px)'   // the pages' .layout is one column at 1100px and below
const GAP = 16
export const vSideColumn = {
  mounted(el) {
    const main = el.closest('.main')
    if (!main) return
    const media = window.matchMedia(WIDE)
    const update = () => {
      if (!media.matches) {
        Object.assign(el.style, { position: '', top: '', maxHeight: '', overflowY: '' })
        return
      }
      const sticky = main.querySelector('.stickyTop')
      const covered = sticky && getComputedStyle(sticky).position === 'sticky' ? sticky.offsetHeight : 0
      const padTop = parseFloat(getComputedStyle(main).paddingTop) || 0
      // Sticky offsets count from inside .main's padding (see .stickyTop in style.css).
      Object.assign(el.style, {
        position: 'sticky',
        top: `${covered + GAP - padTop}px`,
        maxHeight: `${main.clientHeight - covered - GAP * 2}px`,
        overflowY: 'auto',
      })
    }
    const observer = new ResizeObserver(update)
    observer.observe(main)
    const sticky = main.querySelector('.stickyTop')
    if (sticky) observer.observe(sticky)   // a banner coming or going changes the header's height
    media.addEventListener('change', update)
    el._sideColumn = { observer, media, update }
    update()
  },
  unmounted(el) {
    const s = el._sideColumn
    if (!s) return
    s.observer.disconnect()
    s.media.removeEventListener('change', s.update)
  },
}
