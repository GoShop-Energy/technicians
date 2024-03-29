# -*- coding: utf-8 -*-

{
    'name': 'Bonuses GSE',
    'author': "Sébastien Bühl, Shortcut1337",
    'website': "http://www.goshop.energy",
    'version': '0.1',
    'category': 'Hidden',
    'license': 'LGPL-3',
    'summary': 'Transport Expenses for Technicians and Project Manager',
    'description': """
Compute automatically the transport expenses for the technicians and project manager.

When a SO has a SOL related to a task (the SOL.task_id field should
be set), it should generates commissions to technicians.

SOL generates tasks when the SOL product is configured to do so. It
is done through the `service_tracking` ("Create on Order") field.
In GoShop, "labor" ("main d'oeuvre") products are configured to do
so.

Note that such SOL are considered delivered once its related task is
marked as done.

The commissions are calculated as follows (in the case of GoShop):
- When an SO is validated, it generates one task for each different
"labor" SOL.
- One or more technicians will work on a task
- Technicians will timesheet their worked hours on a task

From there, for a given SO, we need to:
1. Sum up the hours worked on a SOL's task, which is the total of
worked hours per technicians for this task.
2. Get the % commission for this SOL product.
3. Calculate the commission amount for this task/SOL
4. Divide that amount by the total worked hour (point 1.)
5. For each technician, multiply that new amount by their worked
hour.
=> That will generate all the commission per technicians for this
task/SO
6. Repeat for any possible other labor SOL on the SO.

With that, we can figure what should be the commission per
technician, example:

- A SO with those 2 labor SOL:

1. 1 "labor generator" for 300$ amount / 10% rate
2. 1 "labor installation" for 100$ amount / 50% rate

- Which generated the following tasks:

1. labor generator = 10h worked all technicians included
2. labor Installation = 50h worked all technicians included

- With the following detailed worked hours:

1. Tech 1 = 10h on labor generator
2. Tech 2 = 20h on labor Installation
3. Tech 1 = 30h on labor Installation

Commission should be:
- Tech 1 worked 10h (out of 10h) on generator labor task (300$) with
a 10% rate = 10/10th of 10% of 300$ = 30$ commission
- Tech 1 also worked 30h (out of 50h) on Installation labor task (100$)
with a 50% rate = 30/50th of 50% of 100$ = 30$ commission
- Tech 2 worked 20h (out of 50) on Installation labor task (100$) with
a 50% rate = 20/50th of 50% of 100$ = 20$ commission
    """,
    'depends': [
        'hr_contract',
        'industry_fsm',
        'sale_project',
        'sale_stock',
        'sale_timesheet',  # should be auto-installed as `industry_fsm` depends from `hr_timesheet`, but still..
    ],
    'demo': [
        'data/demo.xml',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_views.xml',
        'views/bonus_views.xml',
        'views/hr_views.xml',
        'views/product_views.xml',
        'views/project_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
}
