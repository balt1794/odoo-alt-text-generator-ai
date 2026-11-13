# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AltTextBulk(models.TransientModel):
    _name = 'alt.text.bulk'
    _description = 'Bulk alt text generation'

    name = fields.Char(default='Bulk Alt Text', readonly=True)
    line_ids = fields.One2many('alt.text.bulk.line', 'bulk_id', string='Items')
    summary = fields.Text(readonly=True)
    include_existing = fields.Boolean(string='Show images with alt text')
    credits_left = fields.Char(compute='_compute_credits')
    selected_count = fields.Integer(compute='_compute_selected_count')
    not_enough_credits = fields.Boolean(compute='_compute_selected_count')

    @api.model
    def _scan(self, include_existing=False):
        """Return the One2many commands for every item that needs alt text.

        With `include_existing`, items that already have alt text are listed too: they show their
        current text and start unticked, so nothing is rewritten (and no credit spent) by accident.
        """
        commands = []
        for page in self.env['website.page'].search([('view_id', '!=', False)]):
            missing = page._alt_text_missing_sources()
            for src in page._alt_text_missing_sources(include_existing=include_existing):
                has_alt = src not in missing
                commands.append((0, 0, {
                    'kind': _('Page'),
                    'res_model': 'website.page',
                    'res_id': page.id,
                    'src': src,
                    'thumb_url': src,
                    'name': page.name or page.url,
                    'had_alt': has_alt,
                    'selected': not has_alt,
                    'alt_text': page._alt_text_for_src(src) if has_alt else False,
                }))
        return commands

    @api.onchange('include_existing')
    def _onchange_include_existing(self):
        self.line_ids = [(5, 0, 0)] + self._scan(self.include_existing)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        # Opening the screen reads the live balance, so credits bought elsewhere show up at once.
        try:
            self.env['alt.text.client'].fetch_credits()
        except UserError:
            pass
        if 'line_ids' in fields_list:
            values['line_ids'] = self._scan()
        return values

    def _compute_credits(self):
        credits_left = self.env['ir.config_parameter'].sudo().get_param('alt_text_generator_ai.credits_left')
        for wizard in self:
            wizard.credits_left = credits_left or _('unknown')

    @api.depends('line_ids.selected')
    def _compute_selected_count(self):
        credits_left = self.env['ir.config_parameter'].sudo().get_param('alt_text_generator_ai.credits_left')
        for wizard in self:
            wizard.selected_count = len(wizard.line_ids.filtered('selected'))
            wizard.not_enough_credits = bool(
                credits_left and credits_left.isdigit() and wizard.selected_count > int(credits_left))

    def action_generate(self):
        self.ensure_one()
        done = 0
        stopped = None
        for line in self.line_ids.filtered('selected'):
            record = self.env[line.res_model].browse(line.res_id).exists()
            if not record:
                continue
            try:
                if line.res_model == 'website.page':
                    record.action_generate_alt_text(srcs=[line.src], overwrite=line.had_alt)
                    alt_text = record._alt_text_for_src(line.src)
                else:
                    record.action_generate_alt_text()
                    alt_text = record.name
                written = bool(alt_text)
            except UserError as error:
                line.result = _('Stopped')
                stopped = error.args[0]
                break
            line.write({
                'result': _('Done') if written else _('Skipped'),
                'alt_text': alt_text if written else False,
                'selected': False,
            })
            done += written
        summary = _('Alt text added to %s image(s).', done)
        if stopped:
            summary += '\n' + stopped
        self.summary = summary
        return self._reopen()

    def action_select_all(self):
        self.line_ids.filtered(lambda line: not line.result).write({'selected': True})
        return self._reopen()

    def action_select_none(self):
        self.line_ids.write({'selected': False})
        return self._reopen()

    def _reopen(self):
        # Refresh the open form in place; opening it again would add a breadcrumb every time.
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}


class AltTextBulkLine(models.TransientModel):
    _name = 'alt.text.bulk.line'
    _description = 'Bulk alt text image'

    bulk_id = fields.Many2one('alt.text.bulk', required=True, ondelete='cascade')
    selected = fields.Boolean(default=True)
    kind = fields.Char()
    name = fields.Char(string='Name')
    res_model = fields.Char()
    res_id = fields.Integer()
    src = fields.Char()
    thumb_url = fields.Char()
    result = fields.Char()
    alt_text = fields.Char(string='Alt text')
    had_alt = fields.Boolean()
