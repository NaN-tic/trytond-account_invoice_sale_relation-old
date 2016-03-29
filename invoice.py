# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import If, Eval, Bool
from trytond import backend
from trytond.transaction import Transaction

from sql import Cast
from sql.operators import Concat

__all__ = ['Invoice', 'InvoiceLine']

_STATES = {
    'invisible': If(Bool(Eval('_parent_invoice')),
        Eval('_parent_invoice', {}).get('type') != 'out',
        Eval('invoice_type') != 'out'),
}


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'
    shipments = fields.Function(
        fields.Many2Many('stock.shipment.out', None, None,
            'Customer Shipments',
            states={
                'invisible': Eval('type') != 'out',
                }), 'get_shipments', searcher='search_shipments')
    shipment_returns = fields.Function(
        fields.Many2Many('stock.shipment.out.return', None, None,
            'Customer Return Shipments',
            states={
                'invisible': Eval('type') != 'out',
                }), 'get_shipment_returns', searcher='search_shipment_returns')

    def get_shipments(self, name):
        return list(set([s.id for l in self.lines if l.shipments
                        for s in l.shipments]))

    def get_shipment_returns(self, name):
        return list(set([s.id for l in self.lines if l.shipment_returns
                        for s in l.shipment_returns]))

    @classmethod
    def search_shipments(cls, name, clause):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        InvoiceLineStockMove = pool.get('account.invoice.line-stock.move')
        StockMove = pool.get('stock.move')
        Shipment = pool.get('stock.shipment.out')
        invoice_line = InvoiceLine.__table__()
        invoice_line_stock_move = InvoiceLineStockMove.__table__()
        stock_move = StockMove.__table__()

        clause = Shipment.search_rec_name(name, clause)
        tables, condition = Shipment.search_domain(clause)
        shipment = tables[None][0]
        _, shipment_type = StockMove.shipment.sql_type()
        query = (invoice_line
            .join(invoice_line_stock_move,
                condition=invoice_line.id ==
                invoice_line_stock_move.invoice_line)
            .join(stock_move,
                condition=invoice_line_stock_move.stock_move == stock_move.id)
            .join(shipment,
                condition=stock_move.shipment == Concat('stock.shipment.out,',
                    Cast(shipment.id, shipment_type)))
            .select(invoice_line.invoice,
                where=condition))
        return [('id', 'in', query)]

    @classmethod
    def search_shipment_returns(cls, name, clause):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        InvoiceLineStockMove = pool.get('account.invoice.line-stock.move')
        StockMove = pool.get('stock.move')
        Shipment = pool.get('stock.shipment.out.return')
        invoice_line = InvoiceLine.__table__()
        invoice_line_stock_move = InvoiceLineStockMove.__table__()
        stock_move = StockMove.__table__()

        clause = Shipment.search_rec_name(name, clause)
        tables, condition = Shipment.search_domain(clause)
        shipment = tables[None][0]
        _, shipment_type = StockMove.shipment.sql_type()
        query = (invoice_line
            .join(invoice_line_stock_move,
                condition=invoice_line.id ==
                invoice_line_stock_move.invoice_line)
            .join(stock_move,
                condition=invoice_line_stock_move.stock_move == stock_move.id)
            .join(shipment,
                condition=stock_move.shipment ==
                Concat('stock.shipment.out.return,',
                    Cast(shipment.id, shipment_type)))
            .select(invoice_line.invoice,
                where=condition))
        return [('id', 'in', query)]

    @classmethod
    def view_attributes(cls):
        return super(Invoice, cls).view_attributes() + [
            ('/form/notebook/page[@id="sales"]', 'states', {
                    'invisible': Eval('type') != 'out',
                    })]


class InvoiceLine:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice.line'
    sale = fields.Function(fields.Many2One('sale.sale', 'Sale',
            states=_STATES), 'get_sale')
    shipments = fields.Function(fields.One2Many('stock.shipment.out', None,
            'Customer Shipments', states=_STATES),
        'get_shipments', searcher='search_shipments')
    shipment_returns = fields.Function(
        fields.One2Many('stock.shipment.out.return', None,
            'Customer Return Shipments', states=_STATES),
        'get_shipment_returns', searcher='search_shipment_returns')
    shipment_info = fields.Function(fields.Char('Customer Shipment Info',
            states=_STATES), 'get_shipment_info')

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        super(InvoiceLine, cls).__register__(module_name)
        cursor = Transaction().connection.cursor()

        # Migration from 3.0: Change relation between 'account_invoice_line'
        # and 'stock.move from o2m to m2m
        Move = Pool().get('stock.move')
        table = TableHandler(Move, module_name)
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

    @classmethod
    def search_shipments(cls, name, clause):
        pool = Pool()
        InvoiceLineStockMove = pool.get('account.invoice.line-stock.move')
        StockMove = pool.get('stock.move')
        Shipment = pool.get('stock.shipment.out')
        invoice_line_stock_move = InvoiceLineStockMove.__table__()
        stock_move = StockMove.__table__()

        clause = Shipment.search_rec_name(name, clause)
        tables, condition = Shipment.search_domain(clause)
        shipment = tables[None][0]
        _, shipment_type = StockMove.shipment.sql_type()
        query = (invoice_line_stock_move
            .join(stock_move,
                condition=invoice_line_stock_move.stock_move == stock_move.id)
            .join(shipment,
                condition=stock_move.shipment == Concat('stock.shipment.out,',
                    Cast(shipment.id, shipment_type)))
            .select(invoice_line_stock_move.invoice_line,
                where=condition))
        return [('id', 'in', query)]

    @classmethod
    def search_shipment_returns(cls, name, clause):
        pool = Pool()
        InvoiceLineStockMove = pool.get('account.invoice.line-stock.move')
        StockMove = pool.get('stock.move')
        Shipment = pool.get('stock.shipment.out.return')
        invoice_line_stock_move = InvoiceLineStockMove.__table__()
        stock_move = StockMove.__table__()

        clause = Shipment.search_rec_name(name, clause)
        tables, condition = Shipment.search_domain(clause)
        shipment = tables[None][0]
        _, shipment_type = StockMove.shipment.sql_type()
        query = (invoice_line_stock_move
            .join(stock_move,
                condition=invoice_line_stock_move.stock_move == stock_move.id)
            .join(shipment,
                condition=stock_move.shipment ==
                Concat('stock.shipment.out.return,',
                    Cast(shipment.id, shipment_type)))
            .select(invoice_line_stock_move.invoice_line,
                where=condition))
        return [('id', 'in', query)]

    def get_shipment_info(self, name):
        info = ','.join([s.code for s in self.shipments] +
            [s.code for s in self.shipment_returns])
        return info
