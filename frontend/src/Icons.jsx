import React from 'react';

const paths = {
  book: 'M3 5c3-1 6-1 9 1v13c-3-2-6-2-9-1z M12 6c3-2 6-2 9-1v13c-3-1-6-1-9 1 M6 8l3 1 M15 9l3-1',
  panel: 'M3 4h18v16H3z M9 4v16', plus: 'M12 5v14 M5 12h14',
  search: 'M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0 M15 15l5 5',
  chat: 'M4 4h16v13H9l-5 4z', trash: 'M4 6h16 M9 6V3h6v3 M7 7l1 14h8l1-14',
  moon: 'M19 15A8 8 0 0 1 9 4a8.5 8.5 0 1 0 10 11Z', sun: 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M12 1v3 M12 20v3 M1 12h3 M20 12h3 M4 4l2 2 M18 18l2 2 M4 20l2-2 M18 6l2-2',
  arrow: 'M12 19V5 M5 12l7-7 7 7', open: 'M7 17L18 6 M7 6h11v11',
  copy: 'M8 8h12v13H8z M16 8V3H3v13h5', clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 6v6l4 2',
  scales: 'M12 3v17 M6 20h12 M4 7l16-2 M5 7l-3 7h6z M18 6l-3 7h6z',
  list: 'M8 6h12 M8 12h12 M8 18h12 M3 6h1 M3 12h1 M3 18h1',
};

export function Icon({name, size=18}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}
export function Mark({large=false}) {
  return <span aria-hidden="true" className={'mark' + (large ? ' large' : '')}><Icon name="book" size={large ? 32 : 18}/></span>;
}
