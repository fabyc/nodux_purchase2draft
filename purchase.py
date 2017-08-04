# -*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
import psycopg2
from decimal import Decimal
import StringIO
from trytond.pyson import Eval
from trytond.model import ModelSQL, Workflow, fields, ModelView
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.wizard import Wizard, StateAction, StateView, StateTransition, \
    Button
__all__ = ['PurchasetoDraftStart', 'PurchasetoDraft']
__metaclass__ = PoolMeta

class PurchasetoDraftStart(ModelView):
    'Purchase to Draft Start'
    __name__ = 'purchase_to_draft.start'


class PurchasetoDraft(Wizard):
    'Purchase To Draft'
    __name__ = 'purchase_to_draft'

    start = StateView('purchase_to_draft.start',
        'nodux_purchase2draft.purchase_to_draft_start_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Draft', 'draft_', 'tryton-ok', default=True),
        ])
    draft_ = StateAction('purchase.act_purchase_form')
    #accept = StateTransition()

    def do_draft_(self, action):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        Invoice = pool.get('account.invoice')
        Withholding = Pool().get('account.withholding')
        Module = pool.get('ir.module.module')
        purchases = Purchase.browse(Transaction().context['active_ids'])
        ModelData = pool.get('ir.model.data')
        User = pool.get('res.user')
        Group = pool.get('res.group')
        if_withholdings_module = Module.search([('name', '=', 'nodux_account_withholding_in_ec'), ('state', '=', 'installed')])

        def in_group():
            origin = str(purchases)
            group = Group(ModelData.get_id('nodux_purchase2draft',
                    'group_purchase_draft'))
            transaction = Transaction()

            user_id = transaction.user
            if user_id == 0:
                user_id = transaction.context.get('user', user_id)
            if user_id == 0:
                return True
            user = User(user_id)
            return origin and group in user.groups

        for purchase in purchases:
            if not in_group():
                self.raise_user_error('No tiene permiso para modificar la compra %s', purchase.number)
            else:
                purchase.state = 'draft'
                cursor = Transaction().cursor
                for invoice in purchase.invoices:
                    if if_withholdings_module:
                        withholdingss = Withholding.search([('number', '=', invoice.ref_withholding), ('fisic', '=', False)])
                        if withholdings:
                            for withholding in withholdings:
                                if withholding.estado_sri == 'AUTORIZADO':
                                    self.raise_user_error('No puede reversar una factura que ya ha sido AUTORIZADA')
                                else:
                                    cursor.execute('DELETE FROM account_move_line WHERE move = %s' %withholding.move.id)
                                    cursor.execute('DELETE FROM account_move WHERE id = %s' %withholding.move.id)

                                    cursor.execute('DELETE FROM account_withholding WHERE id =%s' %withholding.id)
                                    cursor.execute('DELETE FROM account_withholding_tax WHERE withholding = %s' %withholding.id)

                    if invoice.move:
                            cursor.execute('DELETE FROM account_move_line WHERE move = %s' %invoice.move.id)
                            cursor.execute('DELETE FROM account_move WHERE id = %s' %invoice.move.id)

                    cursor.execute('DELETE FROM account_invoice WHERE id = %s' %invoice.id)

                for move in purchase.moves:
                    cursor.execute('DELETE FROM stock_move WHERE id = %s' % move.id)

                for shipment in purchase.shipments:
                    if incoming_moves:
                        for incoming in incoming_moves:
                            cursor.execute('DELETE FROM stock_move WHERE id =%s' %incoming.id)
                    if inventory_moves:
                        for inventory in inventory_moves:
                            cursor.execute('DELETE FROM stock_move WHERE id =%s' %inventory.id)
                    if moves:
                        for move in moves:
                            cursor.execute('DELETE FROM stock_move WHERE id =%s' %inventory.id)

                    cursor.execute('DELETE FROM stock_shipment_in WHERE id =%s' %shipment.id)

                purchase.invoice_state = 'none'
                purchase.shipment_state = 'none'

                purchase.save()
