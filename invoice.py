#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta

__all__ = ['Invoice', 'InvoiceLine']

__metaclass__ = PoolMeta


class Invoice():
    __name__ = 'account.invoice'
    sales = fields.Function(fields.Many2Many('sale.sale', None, None, 'Sales'),
        'get_sales')

    @classmethod
    def get_sales(cls, invoices, name):
        origins = {}
        for invoice in invoices:
            origins[invoice.id] = list(set(
                    [l.sale for l in invoice.lines if l.sale]))
        return origins


class InvoiceLine():
    __name__ = 'account.invoice.line'

    sale = fields.Function(fields.Many2One('sale.sale', 'Sale'), 'get_sale')

    def get_sale(self, name):
        SaleLine = Pool().get('sale.line')
        if isinstance(self.origin, SaleLine):
            return self.origin.sale.id
