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
