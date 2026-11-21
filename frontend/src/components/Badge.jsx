import React from 'react';

export function Badge({ level, className = '' }) {
  const lvl = (level || 'Low').toLowerCase();
  return (
    <span className={`badge ${lvl} ${className}`}>
      {level || 'Low'}
    </span>
  );
}
