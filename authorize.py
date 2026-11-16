"""Autorització única del canal (OAuth). Genera el refresh token per a upload.py.

1) python3 authorize.py url CLIENT_SECRET.json      -> imprimeix l'enllaç per autoritzar
2) python3 authorize.py token CLIENT_SECRET.json "URL_DE_RETORN"   -> imprimeix el refresh token
L'URL de retorn és la de 127.0.0.1 que el navegador mostra (encara que digui que no carrega)."""
import sys

from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
REDIRECT = "http://127.0.0.1:8765/"


def flow(secret):
    f = Flow.from_client_secrets_file(secret, scopes=SCOPES, redirect_uri=REDIRECT)
    return f


if __name__ == "__main__":
    cmd, secret = sys.argv[1], sys.argv[2]
    f = flow(secret)
    verifier_file = secret + ".verifier"
    if cmd == "url":
        url, _ = f.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
        if f.code_verifier:  # PKCE: el verificador s'ha de reutilitzar al pas 2
            open(verifier_file, "w").write(f.code_verifier)
        print(url)
    else:
        import os
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # retorn a 127.0.0.1 (http), estàndard per a apps d'escriptori
        if os.path.exists(verifier_file):
            f.code_verifier = open(verifier_file).read().strip()
        f.fetch_token(authorization_response=sys.argv[3])
        print(f.credentials.refresh_token)
