// Diagnostic reference only: keep in sync with site/_headers (covered by tests).
// These values are never applied to responses by this report-only module.
export const ASSET_SECURITY_POLICY=Object.freeze({
 'Strict-Transport-Security':'max-age=86400',
 'X-Content-Type-Options':'nosniff',
 'Referrer-Policy':'strict-origin-when-cross-origin',
 'X-Frame-Options':'DENY',
 'Permissions-Policy':'camera=(), microphone=(), geolocation=(), payment=()'
});
export function reportSecurityHeaders(response,{log=event=>console.info(event)}={}){
 const missing=Object.keys(ASSET_SECURITY_POLICY).filter(name=>!response.headers.has(name));
 // Only fixed policy names are logged: no request, URL, values, cookies or IDs.
 if(missing.length){try{log({event:'security_headers_report_only',missing_headers:missing});}catch{/* Diagnostics must not interrupt the response. */}}
 // Redirect responses can have immutable headers. Copy without consuming the body.
 const headers=new Headers(response.headers);
 headers.set('X-O4Z-Security-Mode','report-only');
 return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}
