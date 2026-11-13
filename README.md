# Alt Text Generator AI for Odoo

Write SEO-friendly image alt text for your Odoo website with AI, in 131 languages.
Missing alt text hurts search ranking and accessibility. These modules find the images
that need it and write a clear description for each one.

## Modules

| Module | What it does |
| --- | --- |
| `alt_text_generator_ai` | Alt text for website page images, the **Bulk Alt Text** screen, settings (API key, language, credits). Depends on `website`. |
| `alt_text_generator_ai_sale` | Adds alt text for eCommerce product images. Installs automatically when `website_sale` is installed. |

## Branches

One branch per Odoo version, named exactly like the version: `19.0` is the current one.

## Install

1. Copy both folders into your Odoo `addons` path (or add this repository to it) and update the apps list.
2. Install **Alt Text Generator AI** (the shop add-on follows automatically with Website Sales).
3. Create a free account at <https://alttextgeneratorai.com/dashboard> and copy your API key.
4. In Odoo go to **Settings > Alt Text Generator AI**, paste the key, pick a language and save.
5. Open **Website > Site > Bulk Alt Text**, tick the images and press **Generate Alt Text for Selected**.

You can also select pages in **Website > Site > Pages** and use **Actions > Generate Missing Alt Text**,
or press **Generate Alt Text** on an extra product image.

## External service

An image is sent to [alttextgeneratorai.com](https://alttextgeneratorai.com) only when you press a Generate
button. It needs an API key from your own account. One credit is used per image. See the
[privacy policy](https://alttextgeneratorai.com/privacy-policy) and [pricing](https://alttextgeneratorai.com/pricing).

## Tests

```bash
odoo -d <database> -i alt_text_generator_ai,alt_text_generator_ai_sale --test-tags /alt_text_generator_ai,/alt_text_generator_ai_sale --stop-after-init
```

## License

LGPL-3. See [LICENSE](LICENSE).
