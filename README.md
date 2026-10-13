# LCD Manager

A Django application for managing LCD inventory, brands, purchase and selling prices, and a manually maintained wallet balance. The application has a Persian, right-to-left interface and supports bulk stock updates and Excel exports.

## Contents

- [Features](#features)
- [Technology and requirements](#technology-and-requirements)
- [Local setup](#local-setup)
- [Usage](#usage)
- [Application routes](#application-routes)
- [Project structure and models](#project-structure-and-models)
- [Checks and tests](#checks-and-tests)
- [Configuration and deployment](#configuration-and-deployment)
- [Maintenance and troubleshooting](#maintenance-and-troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- Create, view, edit, and delete LCD products with a title, optional brand, purchase price, selling price, current stock, and initial stock.
- Create and edit brands, and browse their associated products.
- Search products and brands by title or slug.
- Switch between products with available stock and products with zero or unspecified stock.
- Sort products by stock quantity or purchase price; the default order shows the newest products first.
- Browse the main inventory list in pages of 20 products, preserving search and filter settings between pages.
- Update stock quantities in bulk from the main inventory list or a brand page, with input validation and transactional writes.
- View total inventory quantity and wallet balance on the main page.
- Export all inventory products to an Excel workbook.
- Manage products, brands, and wallets through the Django admin panel.
- Generate unique slugs automatically, including for Persian titles, and preserve existing URLs when titles change.
- Protect brands from deletion while products are still assigned to them.

## Technology and requirements

| Component | Version or details |
| --- | --- |
| Python | 3.12 or later, as required by the installed Django package |
| Django | `6.0.6` |
| Database | SQLite, stored locally in `db.sqlite3` |
| Excel export | `openpyxl==3.1.5` |
| Frontend | Django templates, HTML, CSS, and JavaScript |
| Interface font | Vazirmatn, loaded from Google Fonts |

Dependencies are pinned in [requirements.txt](requirements.txt). Alongside Django and openpyxl, the file includes `asgiref`, `sqlparse`, `tzdata`, and `et_xmlfile`. The application does not require Node.js or a separate database server. Git is needed if you clone the repository.

## Local setup

### 1. Get the project

```bash
git clone https://github.com/miladaxel/LCD-manager.git
cd LCD-manager
```

If you already have the project, open a terminal in the directory containing `manage.py` and continue with the next step.

### 2. Create a virtual environment and install dependencies

Check your Python version with `python --version` or `python3 --version`. Use Python 3.12 or later.

**Windows / PowerShell**

These commands use the virtual environment's interpreter directly, so environment activation is unnecessary.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Initialize the database and create an administrator

**Windows / PowerShell**

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

**Linux / macOS, with the virtual environment activated**

```bash
python manage.py migrate
python manage.py createsuperuser
```

The `migrate` command creates or updates the database tables. Follow the prompts from `createsuperuser` to create an account for the admin panel. The SQLite database is created in the project root. No sample inventory data is added automatically.

### 4. Initialize the wallet

Complete this step if you want to use the wallet section. The main page displays the first `Wallet` record, while its edit link points specifically to wallet ID **1**. For a fresh database, create the initial record with:

**Windows / PowerShell**

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from LCD.models import Wallet; Wallet.objects.get_or_create(pk=1, defaults={'balance': 0})"
```

**Linux / macOS**

```bash
python manage.py shell -c "from LCD.models import Wallet; Wallet.objects.get_or_create(pk=1, defaults={'balance': 0})"
```

If wallet ID 1 already exists, this command leaves its balance unchanged. Keep a single wallet with ID 1 for the current interface; the model itself does not enforce a single-wallet constraint.

### 5. Start the development server

**Windows / PowerShell**

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

**Linux / macOS**

```bash
python manage.py runserver
```

- Application: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Admin panel: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

Press `Ctrl+C` in the terminal to stop the server.

## Usage

The interface remains in Persian; the instructions below describe its controls in English.

### Add brands and products

1. Create a brand using the new-brand option.
2. Open the new-LCD page and enter the product title, purchase price, selling price, and quantity.
3. Select a brand if applicable. Products can also be saved without a brand.
4. Enter initial stock separately. It is not copied automatically from current stock and does not change when current stock is updated.
5. After saving, products with positive stock appear in the default inventory list. Use the zero-stock toggle to display products without available stock.

Prices and wallet balances are stored as integers. The models do not define a currency, so use a consistent unit, such as toman, when entering values.

### Search and update inventory

On the main page, search for products, switch the stock filter, or sort by quantity or purchase price. Products whose quantity is `NULL` are included in the zero-stock group.

To update multiple quantities, edit the inputs on the main inventory list or a brand page and submit the form. On the main list, the form submits products from the current page only. If any submitted value is invalid, or a database write fails, none of that request's quantity changes are saved.

- Bulk quantity inputs accept integers from `0` to `2147483647`.
- The quantity form on the product detail page accepts integers from `1` to `2147483647`.
- The total inventory quantity displayed on the main page covers all products, regardless of the active filters or current page.

**Current behavior of the Sell button:** despite its label on the product detail page, the `sell_lcd` method assigns the submitted quantity directly as the new stock level. For example, submitting `3` for a product with stock `10` changes its stock to **3**. It does not subtract units, record a sale transaction, or increase the wallet balance.

### Manage the wallet

Use the wallet edit icon on the main page or the `Wallet` section in the admin panel to update the balance manually. Wallet changes are independent of product prices and stock updates.

### Export inventory to Excel

Use the Excel export option on the main page, or open `/export/excel/`. The application downloads `lcd_inventory.xlsx` with a worksheet named `LCD`.

The workbook contains the following columns, with Persian headers:

| Position | Column |
| --- | --- |
| 1 | Title |
| 2 | Brand |
| 3 | Quantity |
| 4 | Purchase price |
| 5 | Selling price |
| 6 | Initial quantity |
| 7 | Slug |
| 8 | Last updated |

The export includes **all products**. Search terms, stock filters, and pagination do not affect it. Unspecified quantities are exported as zero. Importing inventory from Excel is not implemented.

### Delete records

Products can be deleted from their detail page after a confirmation step. Brands can be deleted through the admin panel, but deletion is blocked while any products reference the brand. Reassign those products or clear their brand field before deleting the brand.

## Application routes

| Route | Purpose |
| --- | --- |
| `/` | Product list, search, filters, and bulk quantity updates |
| `/create/` | Create a product |
| `/lcd/<slug>` | Product details and the form labeled Sell |
| `/<slug>/update/` | Edit a product |
| `/<slug>/delete/` | Confirm and delete a product |
| `/brands/` | List and search brands |
| `/brand/create/` | Create a brand |
| `/brand/<slug>/` | Brand products and bulk quantity updates |
| `/brand_update/<slug>/` | Edit a brand title |
| `/wallet/<pk>/` | Edit a wallet balance |
| `/export/excel/` | Download the Excel export |
| `/admin/` | Django admin panel |

`<slug>` identifies a product or brand, and `<pk>` is a wallet's numeric primary key. The product detail route, `/lcd/<slug>`, has **no trailing slash** in the current URL configuration.

The main inventory page supports these query parameters:

| Parameter | Values and behavior |
| --- | --- |
| `q` | Search within the product title or slug |
| `stock` | `zero` selects zero or unspecified stock; the default and other values select positive stock |
| `sort` | `quantity`, `-quantity`, `buy_price`, or `-buy_price`; the default and invalid values use `-created_at` |
| `page` | A page number or `last` |

For example, `/?q=samsung&stock=available&sort=-buy_price&page=2` shows the second page of matching products with positive stock, ordered by purchase price from highest to lowest. Brand detail pages support the same `sort` options, and the brand list supports `q`.

## Project structure and models

```text
LCD-manager/
├── manage.py
├── requirements.txt
├── README.md
├── Dayi_iman_lcd/
│   ├── settings.py              # Django and database settings
│   ├── urls.py                  # Root routes and admin panel
│   ├── asgi.py
│   └── wsgi.py
├── LCD/
│   ├── models.py                # LCD, Brand, and Wallet models
│   ├── views.py                 # Pages, stock updates, and Excel export
│   ├── forms.py                 # Quantity input validation
│   ├── url.py                   # App routes under the LCD namespace
│   ├── admin.py                 # Admin panel configuration
│   ├── tests.py                 # Application behavior tests
│   ├── migrations/              # Database schema migrations
│   └── static/LCD/css/style.css
└── templates/
    ├── LCD_template/            # Base, product, and brand templates
    └── LCD/wallet_form.html     # Wallet balance form
```

The local `db.sqlite3` database and `.venv` environment are created during setup and are excluded by `.gitignore`.

| Model | Responsibility and fields |
| --- | --- |
| `LCD` | Title, purchase and selling prices, current and initial quantities, optional brand, unique slug, and creation/update timestamps |
| `Brand` | Title, unique slug, and creation/update timestamps; related products are accessible through `brand.lcd` |
| `Wallet` | An integer wallet balance |

`LCD` and `Brand` inherit from the abstract `SluggedModel`. Missing slugs are generated on save, and colliding titles receive different slugs. Titles that produce no ASCII slug receive a generated identifier. Existing slugs are preserved when titles change.

## Checks and tests

**Windows / PowerShell**

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test LCD
```

**Linux / macOS, with the virtual environment activated**

```bash
python manage.py check
python manage.py test LCD
```

Tests use a separate test database. Current coverage includes quantity validation, rollback after failed writes, preventing updates to another brand's products through a brand page, pagination and filter preservation, unique slug generation, and protecting products when a brand is deleted.

After changing models, run these commands using the virtual environment's interpreter:

```bash
python manage.py makemigrations LCD
python manage.py migrate
```

In PowerShell, replace `python` with `.\.venv\Scripts\python.exe` if you have not activated the environment. Commit new migrations alongside the corresponding model changes.

## Configuration and deployment

Configuration lives in [Dayi_iman_lcd/settings.py](Dayi_iman_lcd/settings.py). The current settings target local development:

- `DEBUG=True` and `ALLOWED_HOSTS=[]`.
- `SECRET_KEY` is defined directly in the settings file.
- Django's language setting is `en-us` and its timezone is `UTC`; application templates use Persian and a right-to-left layout.
- The project does not load `.env` files. Environment variable support must be added to the settings before using that configuration approach.
- Main application pages, data changes, and Excel exports are not restricted by login or administrator permissions. The admin panel at `/admin/` requires an authorized account.
- The interface font is fetched from Google Fonts and requires internet access to load.

Before deploying, configure a separate secret key, disable debug mode, define allowed hosts and application access controls, and complete HTTPS and static-file settings. Set `STATIC_ROOT` before running `collectstatic`; it is not configured in the current project. Use `runserver` for local development, and a compatible application server with [wsgi.py](Dayi_iman_lcd/wsgi.py) or [asgi.py](Dayi_iman_lcd/asgi.py) for deployment.

## Maintenance and troubleshooting

| Problem | Action |
| --- | --- |
| `No module named django` | Install dependencies using the same virtual environment interpreter that runs the application. |
| Django installation fails because of the Python version | Choose Python 3.12 or later and create the virtual environment with that interpreter. |
| `no such table` or a missing database column | Run `manage.py migrate` using the virtual environment interpreter. |
| A product does not appear in the main list | Check its quantity, the zero-stock toggle, the search term, and the current page. |
| The wallet edit link returns 404 | Initialize a `Wallet` record with ID 1 as described in the setup section. |
| A brand cannot be deleted | Reassign its products to another brand or clear their brand references. |
| Port 8000 is already in use | Run `manage.py runserver 8001` and open the application on port 8001. |

Local data is stored in `db.sqlite3`. For a simple local backup, stop the application and any other processes writing to the database, then copy the database file to a separate location. Excel exports omit administrator accounts and wallet records, so they do not replace a complete database backup.

## Contributing

Make changes on a separate branch, verify the affected behavior, and run `check` and `test LCD` before submitting a pull request. Include migrations when models change, and update this README when application behavior changes. Keep local databases, virtual environments, and secrets out of the repository.

## License

The repository currently has no `LICENSE` file. An explicit license for use or redistribution has not been specified.
