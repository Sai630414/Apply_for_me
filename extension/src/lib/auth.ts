/**
 * Google OAuth Authentication Helper for ApplyForMe (Chrome Manifest V3)
 * Uses chrome.identity.launchWebAuthFlow to obtain a verified Google OpenID Connect ID Token.
 */

export async function getGoogleIdToken(): Promise<string> {
  if (typeof chrome === 'undefined' || !chrome.identity || !chrome.identity.launchWebAuthFlow) {
    // Development fallback if testing in Vite dev server preview outside Chrome
    console.warn('[ApplyForMe] chrome.identity not available; using development preview token');
    return 'dev_token_demo_user';
  }

  const manifest = chrome.runtime.getManifest();
  const clientId = manifest.oauth2?.client_id;

  if (!clientId || clientId.includes('YOUR_GOOGLE_CLIENT_ID')) {
    throw new Error(
      'Google Client ID is not configured in manifest.json. Please configure your OAuth Client ID or use Quick Demo Sign In.'
    );
  }

  // Generate cryptographic nonce for OpenID Connect
  const nonceBytes = new Uint8Array(16);
  crypto.getRandomValues(nonceBytes);
  const nonce = Array.from(nonceBytes, (b) => b.toString(16).padStart(2, '0')).join('');

  const redirectUri = chrome.identity.getRedirectURL(); // e.g. https://<extension-id>.chromiumapp.org/

  const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
  authUrl.searchParams.set('client_id', clientId);
  authUrl.searchParams.set('response_type', 'id_token');
  authUrl.searchParams.set('redirect_uri', redirectUri);
  authUrl.searchParams.set('scope', 'openid email profile');
  authUrl.searchParams.set('nonce', nonce);
  authUrl.searchParams.set('prompt', 'select_account');

  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow(
      {
        url: authUrl.toString(),
        interactive: true,
      },
      (redirectResponseUrl) => {
        if (chrome.runtime.lastError) {
          const errMsg = chrome.runtime.lastError.message || 'Google sign-in was cancelled.';
          return reject(new Error(errMsg));
        }

        if (!redirectResponseUrl) {
          return reject(new Error('No response URL returned by Google.'));
        }

        try {
          const url = new URL(redirectResponseUrl);
          // With response_type=id_token, Google returns the token in the URL hash fragment (#id_token=...)
          const hashParams = new URLSearchParams(url.hash.replace(/^#/, ''));
          const idToken = hashParams.get('id_token');

          if (idToken) {
            resolve(idToken);
          } else {
            const error = hashParams.get('error') || url.searchParams.get('error');
            const errorDescription = hashParams.get('error_description') || url.searchParams.get('error_description');
            reject(
              new Error(
                errorDescription || error || 'Could not retrieve ID token from Google redirect.'
              )
            );
          }
        } catch (err: any) {
          reject(new Error(`Failed to parse Google redirect response: ${err.message}`));
        }
      }
    );
  });
}

