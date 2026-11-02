from base64 import b64encode
from html import escape
from importlib.resources import files

CHRISTMAS_GIFS = {
    name: files("santa").joinpath("assets", f"{name}.gif").read_bytes()
    for name in ("tree", "gifts")
}
PREVIEW_IMAGES = {
    name: f"data:image/gif;base64,{b64encode(content).decode('ascii')}"
    for name, content in CHRISTMAS_GIFS.items()
}


def render_html(body: str, image_sources: dict[str, str] | None = None) -> str:
    sources = PREVIEW_IMAGES if image_sources is None else image_sources
    tree = escape(sources["tree"], quote=True)
    gifts = escape(sources["gifts"], quote=True)
    content = escape(body).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>\n")
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; img-src data: cid:; style-src 'unsafe-inline'">
<title>Le courrier du pôle Nord</title>
</head>
<body style="margin:0;padding:16px 8px;background:#a80e2d;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="font-family:'Comic Sans MS','Trebuchet MS',Arial,sans-serif;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
       style="width:100%;max-width:600px;border:6px dashed #ffdc73;background:#fff9e8;">
<tr><td align="center" style="padding:12px;background:#064c38;color:#ffdc73;
                            font-size:22px;letter-spacing:5px;">
🎄 ✨ 🎁 ✨ 🎄 ✨ 🎁 ✨ 🎄
</td></tr>
<tr><td align="center" style="padding:24px 16px 8px;color:#ac1030;">
<p style="margin:0;font-size:12px;font-weight:bold;letter-spacing:3px;">
COURRIER ULTRA SECRET DU PÔLE NORD</p>
<h1 style="margin:14px 0 6px;font-size:42px;line-height:1.15;
           text-shadow:2px 2px #ffdc73;">HO ! HO ! HOOO ! 🎅</h1>
<p style="margin:0;font-size:18px;color:#176044;">
La magie de Noël a frappé ta boîte mail !</p>
</td></tr>
<tr><td align="center" style="padding:16px;">
<img src="{tree}" width="240" height="144"
     alt="Un sapin de Noël scintillant sous la neige"
     style="display:block;max-width:100%;height:auto;border:4px solid #ffdc73;">
</td></tr>
<tr><td style="padding:8px 18px 20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="border:3px solid #c11838;background:#ffffff;">
<tr><td align="center" style="padding:10px;background:#c11838;color:#ffffff;
                            font-size:15px;font-weight:bold;">
💌 TA MISSION CADEAU, SI TU L'ACCEPTES 💌
</td></tr>
<tr><td style="padding:24px 20px;color:#183e31;font-family:Arial,sans-serif;
               font-size:17px;line-height:1.7;overflow-wrap:anywhere;word-break:break-word;">
{content}
</td></tr>
</table>
</td></tr>
<tr><td align="center" style="padding:0 16px 16px;">
<span style="display:inline-block;padding:10px 16px;border:2px dashed #a80e2d;
             color:#a80e2d;font-size:15px;font-weight:bold;">
🤫 CHUT… MÊME LES RENNES NE DOIVENT RIEN SAVOIR !</span>
</td></tr>
<tr><td align="center" style="padding:0 16px 20px;">
<img src="{gifts}" width="240" height="144"
     alt="Des cadeaux de Noël qui dansent, avec des rubans dorés"
     style="display:block;max-width:100%;height:auto;border:4px solid #ffdc73;">
<p style="margin:16px 0 0;color:#176044;font-size:16px;">
Des paillettes, des chaussettes moches et beaucoup d'amour. ❤️</p>
</td></tr>
<tr><td align="center" style="padding:18px 12px;background:#064c38;color:#ffdc73;">
<p style="margin:0;font-size:22px;font-weight:bold;">JOYEUX SECRET SANTA !</p>
<p style="margin:8px 0 0;font-size:13px;">
★ Livraison officielle de la brigade des lutins ★<br>
100 % esprit de Noël · 0 % discrétion vestimentaire</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
