const API_URL=process.env.NEXT_PUBLIC_API_URL??"http://localhost:8000/api";
export type AuthUser={user_id:string;google_sub:string;email:string;name:string;picture?:string|null;email_verified:boolean;is_active:boolean;created_at:string;updated_at:string;last_login_at?:string|null};
export type AuthResponse={success:boolean;message:string;access_token:string;token_type:string;user:AuthUser};
const TOKEN_KEY="studyai.access_token",USER_KEY="studyai.user";

export async function loginWithGoogle(credential:string){const r=await fetch(`${API_URL}/auth/google`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credential})});if(!r.ok)throw new Error("Google login failed");const d:AuthResponse=await r.json();localStorage.setItem(TOKEN_KEY,d.access_token);localStorage.setItem(USER_KEY,JSON.stringify(d.user));return d}

export function demoLogin(){
  if(typeof window==="undefined")return;
  const now=new Date().toISOString();
  const user:AuthUser={
    user_id:"demo_student",
    google_sub:"demo-google-user",
    email:"student@studyai.demo",
    name:"Study AI Student",
    picture:null,
    email_verified:true,
    is_active:true,
    created_at:now,
    updated_at:now,
    last_login_at:now,
  };
  localStorage.setItem(TOKEN_KEY,"demo-study-ai-session");
  localStorage.setItem(USER_KEY,JSON.stringify(user));
}

export function getToken(){return typeof window==="undefined"?null:localStorage.getItem(TOKEN_KEY)}
export function getUser():AuthUser|null{if(typeof window==="undefined")return null;const r=localStorage.getItem(USER_KEY);return r?JSON.parse(r):null}
export function logout(){localStorage.removeItem(TOKEN_KEY);localStorage.removeItem(USER_KEY)}
export async function deleteAccount(){const t=getToken();if(!t)throw new Error("Authentication required");const r=await fetch(`${API_URL}/auth/account`,{method:"DELETE",headers:{Authorization:`Bearer ${t}`}});if(!r.ok)throw new Error("Could not delete account");logout()}
export const api={url:API_URL,fetch:(path:string,init:RequestInit={})=>{const t=getToken();return fetch(`${API_URL}${path}`,{...init,headers:{...(init.headers||{}),...(t?{Authorization:`Bearer ${t}`}:{})}})}}