#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Invoice', 'InvoiceLine', 'Move', 'SaleLine']

__metaclass__ = PoolMeta


class Invoice():
    __name__ = 'account.invoice'
    sales = fields.Function(fields.Many2Many('sale.sale', None, None, 'Sales',
            states={
                'invisible': Eval('type').in_(['in_invoice', 'in_credit_note']),
                }), 'get_sales')
    shipments = fields.Function(
        fields.Many2Many('stock.shipment.out', None, None, 'Shipments',
            states={
                'invisible': Eval('type').in_(['in_invoice', 'in_credit_note',
                    'out_credit_note']),
                }), 'get_shipments')
    shipment_returns = fields.Function(
        fields.Many2Many('stock.shipment.out.return', None, None,
            'Shipment Returns',
            states={
                'invisible': Eval('type').in_(['in_invoice', 'in_credit_note',
                    'out_invoice']),
                }), 'get_shipment_returns')

    def get_sales(self, name):
        return list(set([l.sale.id for l in self.lines if l.sale]))

    def get_shipments(self, name):
        return list(set([s.id for l in self.lines if l.shipments
                        for s in l.shipments]))

    def get_shipment_returns(self, name):
        return list(set([s.id for l in self.lines if l.shipment_returns
                        for s in l.shipment_returns]))


class InvoiceLine():
    __name__ = 'account.invoice.line'
    sale = fields.Function(fields.Many2One('sale.sale', 'Sale',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note']),
                }), 'get_sale')
    moves = fields.One2Many('stock.move', 'invoice_line', 'Moves', readonly=True)
    shipments = fields.Function(fields.One2Many('stock.shipment.out', None,
            'Shipments',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note',
                    'out_credit_note']),
                }), 'get_shipments')
    shipment_returns = fields.Function(
        fields.One2Many('stock.shipment.out.return', None, 'Shipment Returns',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note',
                    'out_invoice']),
                }), 'get_shipment_returns')
    shipment_info = fields.Function(fields.Char('Shipment Info',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note']),
                }), 'get_shipment_info')

    def get_sale(self, name):
        SaleLine = Pool().get('sale.line')
        if isinstance(self.origin, SaleLine):
            return self.origin.sale.id

    def get_shipments_returns(model_name):
        "Computes the returns or shipments"
        def method(self, name):
            Model = Pool().get(model_name)
            shipments = set()
            for move in self.moves:
                if isinstance(move.shipment, Model):
                    shipments.add(move.shipment.id)
            return list(shipments)
        return method

    get_shipments = get_shipments_returns('stock.shipment.out')
    get_shipment_returns = get_shipments_returns('stock.shipment.out.return')

    def get_shipment_info(self, name):
        info = ','.join([s.code for s in self.shipments] +
            [s.code for s in self.shipment_returns])
        return info

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['moves'] = None
        return super(InvoiceLine, cls).copy(lines, default=default)


class Move():
    __name__ = 'stock.move'
    invoice_line = fields.Many2One('account.invoice.line', 'Invoice Line')

    @classmethod
    def copy(cls, moves, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default['invoice_line'] = None
        return super(Move, cls).copy(moves, default=default)


class SaleLine():
    __name__ = 'sale.line'

    def get_invoice_line(self, invoice_type):
        '''
        Return a list of invoice lines for sale line according to invoice_type
        '''
        invoice_lines = super(SaleLine, self).get_invoice_line(invoice_type)
        if (self.type != 'line'
                or self.sale.invoice_method == 'order'
                or not self.product
                or self.product.type == 'service'):
            return invoice_lines

        moves = set()
        for move in self.moves:
            if move.state == 'done':
                moves.add(move.id)

        skip_ids = set(l.id for i in self.sale.invoices_recreated
            for l in i.lines)
        for old_invoice_line in self.invoice_lines:
            if old_invoice_line.type != 'line':
                continue
            if old_invoice_line.id not in skip_ids:
                for m in old_invoice_line.moves:
                    moves.discard(m.id)

        for invoice_line in invoice_lines:
            invoice_line.moves = list(moves)
            
        return invoice_lines
