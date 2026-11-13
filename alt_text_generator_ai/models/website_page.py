# -*- coding: utf-8 -*-
import base64
import logging
import re
from urllib.parse import urlparse

from lxml import etree

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

WEB_IMAGE_ID = re.compile(r'^/web/image/(\d+)(?:-[0-9a-f]+)?(?:/|$)')
WEB_IMAGE_FIELD = re.compile(r'^/web/image/([\w.]+)/(\d+)/(\w+)')
MODULE_STATIC = re.compile(r'^/(\w+)/static/(.+)$')


class WebsitePage(models.Model):
    _inherit = 'website.page'

    def _alt_text_source(self, src):
        """Work out where an <img src> lives: returns {'datas': b64}, {'url': str} or None."""
        src = (src or '').strip()
        if not src or src.startswith('data:'):
            return None
        if re.match(r'^https?://', src, re.I):
            return {'url': src}
        path = urlparse(src).path

        match = WEB_IMAGE_ID.match(path)
        if match:
            attachment = self.env['ir.attachment'].browse(int(match.group(1))).exists()
            return {'datas': attachment.datas} if attachment and attachment.datas else None

        match = WEB_IMAGE_FIELD.match(path)
        if match:
            model, res_id, field = match.group(1), int(match.group(2)), match.group(3)
            if model in self.env and field in self.env[model]._fields \
                    and self.env[model]._fields[field].type == 'binary':
                record = self.env[model].browse(res_id).exists()
                return {'datas': record[field]} if record and record[field] else None
            return None

        match = MODULE_STATIC.match(path)
        if match:
            try:
                with file_open('%s/static/%s' % match.groups(), 'rb') as handle:
                    return {'datas': base64.b64encode(handle.read())}
            except (FileNotFoundError, ValueError, OSError):
                return None

        attachment = self.env['ir.attachment'].search([('url', '=', path)], limit=1)
        return {'datas': attachment.datas} if attachment and attachment.datas else None

    def _alt_text_missing_sources(self, include_existing=False):
        """The different images on this page that have no alt text (one credit each).

        With `include_existing` the images that already have alt text are listed too.
        """
        self.ensure_one()
        if not self.view_id:
            return []
        root = etree.fromstring(self.view_id.arch.encode('utf-8'))
        sources = []
        xpath = '//img' if include_existing else '//img[not(@alt) or normalize-space(@alt)=""]'
        for img in root.xpath(xpath):
            src = img.get('src')
            if src and src not in sources:
                sources.append(src)
        return sources

    def _alt_text_for_src(self, src):
        """The alt text currently set on the first <img> of this page that uses `src`."""
        self.ensure_one()
        if not self.view_id:
            return ''
        root = etree.fromstring(self.view_id.arch.encode('utf-8'))
        for img in root.xpath('//img[@src=$src]', src=src):
            if (img.get('alt') or '').strip():
                return img.get('alt').strip()
        return ''

    def _alt_text_missing_count(self):
        return len(self._alt_text_missing_sources())

    def action_generate_alt_text(self, srcs=None, overwrite=False):
        """Write alt text for the images without it; `srcs` limits it to those image sources.

        With `overwrite` the images in `srcs` get new alt text even if they already have some.
        """
        client = self.env['alt.text.client']
        generated = skipped = 0
        for page in self:
            view = page.view_id
            if not view:
                continue
            root = etree.fromstring(view.arch.encode('utf-8'))
            cache = {}
            changed = False
            xpath = '//img' if overwrite and srcs is not None else '//img[not(@alt) or normalize-space(@alt)=""]'
            for img in root.xpath(xpath):
                src = img.get('src')
                if srcs is not None and src not in srcs:
                    continue
                if not src:
                    skipped += 1
                    continue
                if src not in cache:
                    source = self._alt_text_source(src)
                    if not source:
                        cache[src] = None
                    else:
                        try:
                            cache[src] = client.generate(**source)
                        except UserError:
                            if changed:
                                view.arch = etree.tostring(root, encoding='unicode')
                            raise
                if cache[src]:
                    img.set('alt', cache[src])
                    generated += 1
                    changed = True
                else:
                    skipped += 1
            if changed:
                view.arch = etree.tostring(root, encoding='unicode')

        if not generated and not skipped:
            return client._notification(_('Alt text'), _('Every image already has alt text.'), 'info')
        message = _('Alt text added to %s images.', generated)
        if skipped:
            message += ' ' + _('%s images were skipped (not readable or no source).', skipped)
        return client._notification(_('Alt text'), message, 'success' if generated else 'warning')
