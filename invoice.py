#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond import backend
from trytond.transaction import Transaction

__all__ = ['Invoice', 'InvoiceLine']

__metaclass__ = PoolMeta


class Invoice():
    __name__ = 'account.invoice'
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
    shipments = fields.Function(fields.One2Many('stock.shipment.out', None,
            'Shipments',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note']),
                }), 'get_shipments')
    shipment_returns = fields.Function(
        fields.One2Many('stock.shipment.out.return', None, 'Shipment Returns',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note']),
                }), 'get_shipment_returns')
    shipment_info = fields.Function(fields.Char('Shipment Info',
            states={
                'invisible': Eval('_parent_invoice', {}
                    ).get('type').in_(['in_invoice', 'in_credit_note']),
                }), 'get_shipment_info')

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        super(InvoiceLine, cls).__register__(module_name)
        cursor = Transaction().cursor

        # Migration from 3.0: Change relation between 'account_invoice_line'
        # and 'stock.move from o2m to m2m
        Move = Pool().get('stock.move')
        table = TableHandler(cursor, Move, module_name)
        if table.column_exist('invoice_line'):
            m_table = Move.__table__()
            cursor.execute(*m_table.select(m_table.id, m_table.invoice_line,
                where=m_table.invoice_line != None))
            with Transaction().set_user(0):
                for move_id, invoice_line_id in cursor.fetchall():
                    move = Move(move_id)
                    move.invoice_lines = [invoice_line_id]
                    move.save()
            table.drop_column('invoice_line')

    def get_sale(self, name):
        SaleLine = Pool().get('sale.line')
        if isinstance(self.origin, SaleLine):
            return self.origin.sale.id

    def get_shipments_returns(model_name):
        "Computes the returns or shipments"
        def method(self, name):
            Model = Pool().get(model_name)
            shipments = set()
            for move in self.stock_moves:
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
