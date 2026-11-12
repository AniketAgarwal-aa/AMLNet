const BASE=import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000/api' : '');
export async function api(path,opts={}){
  if(!BASE) throw new Error('The production API URL is not configured. Set VITE_API_BASE_URL in Vercel.');
  const r=await fetch(BASE+path,opts);
  if(!r.ok)throw new Error((await r.json().catch(()=>({detail:r.statusText}))).detail||r.statusText);
  return r.json();
}
