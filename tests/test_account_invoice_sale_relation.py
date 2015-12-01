# This file is part of the account_invoice_sale_relation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class AccountInvoiceSaleRelationTestCase(ModuleTestCase):
    'Test Account Invoice Sale Relation module'
    module = 'account_invoice_sale_relation'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountInvoiceSaleRelationTestCase))
    return suite