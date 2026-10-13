from unittest.mock import patch
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from LCD.models import Brand, LCD


class QuantityUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(title='Test brand')
        cls.first = LCD.objects.create(
            title='First LCD', brand=cls.brand, quantity=10,
            buy_price=100, sell_price=150,
        )
        cls.second = LCD.objects.create(
            title='Second LCD', brand=cls.brand, quantity=20,
            buy_price=100, sell_price=150,
        )
        cls.other = LCD.objects.create(
            title='Other LCD', quantity=30, buy_price=100, sell_price=150,
        )

    def bulk_urls(self):
        return [
            reverse('LCD:lcd_list'),
            reverse('LCD:brand_detail', kwargs={'slug': self.brand.slug}),
        ]

    def stock_state(self):
        return list(LCD.objects.order_by('pk').values_list('pk', 'quantity', 'updated_at'))

    def test_invalid_bulk_values_leave_all_products_unchanged(self):
        for url in self.bulk_urls():
            for value in ('', '   ', 'abc', '-1', '1.5', '2147483648', '9' * 100):
                with self.subTest(url=url, value=value):
                    before = self.stock_state()
                    response = self.client.post(url, {
                        f'quantity_{self.first.slug}': '8',
                        f'quantity_{self.second.slug}': value,
                    }, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'هیچ تغییری ذخیره نشد.')
                    self.assertContains(response, self.second.title)
                    self.assertEqual(self.stock_state(), before)

    def test_valid_bulk_values_include_zero_and_persian_digits(self):
        for url in self.bulk_urls():
            with self.subTest(url=url):
                response = self.client.post(url, {
                    f'quantity_{self.first.slug}': '0',
                    f'quantity_{self.second.slug}': '۱۲',
                })
                self.assertRedirects(response, url)
                self.first.refresh_from_db()
                self.second.refresh_from_db()
                self.other.refresh_from_db()
                self.assertEqual(self.first.quantity, 0)
                self.assertEqual(self.second.quantity, 12)
                self.assertEqual(self.other.quantity, 30)

    def test_omitted_products_are_not_updated(self):
        before = self.second.updated_at
        response = self.client.post(reverse('LCD:lcd_list'), {
            f'quantity_{self.first.slug}': '8',
        })
        self.assertEqual(response.status_code, 302)
        self.second.refresh_from_db()
        self.assertEqual(self.second.quantity, 20)
        self.assertEqual(self.second.updated_at, before)

    def test_brand_update_cannot_change_another_brands_product(self):
        response = self.client.post(self.bulk_urls()[1], {
            f'quantity_{self.first.slug}': '8',
            f'quantity_{self.other.slug}': '5',
        })
        self.assertEqual(response.status_code, 302)
        self.first.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.first.quantity, 8)
        self.assertEqual(self.other.quantity, 30)

    def test_database_failure_rolls_back_entire_batch(self):
        original_save = LCD.sell_lcd
        for url in self.bulk_urls():
            with self.subTest(url=url):
                before = self.stock_state()
                saved = []

                def fail_on_second_save(lcd, quantity):
                    original_save(lcd, quantity)
                    saved.append(lcd.pk)
                    if len(saved) == 2:
                        raise DatabaseError('Simulated write failure')

                with patch.object(LCD, 'sell_lcd', fail_on_second_save):
                    with self.assertLogs('LCD.views', level='ERROR'):
                        response = self.client.post(url, {
                            f'quantity_{self.first.slug}': '8',
                            f'quantity_{self.second.slug}': '12',
                        }, follow=True)
                self.assertEqual(len(saved), 2)
                self.assertContains(response, 'هیچ تغییری ذخیره نشد')
                self.assertEqual(self.stock_state(), before)

    def test_invalid_detail_values_do_not_raise_or_save(self):
        url = reverse('LCD:lcd_detail', kwargs={'slug': self.first.slug})
        payloads = [{}, *({'quantity': value} for value in (
            '', 'abc', '-1', '0', '1.5', '2147483648',
        ))]
        for payload in payloads:
            with self.subTest(payload=payload):
                before = self.stock_state()
                response = self.client.post(url, payload, follow=True)
                self.assertContains(response, 'هیچ تغییری ذخیره نشد.')
                self.assertEqual(self.stock_state(), before)

    def test_valid_detail_value_keeps_existing_quantity_update_behavior(self):
        url = reverse('LCD:lcd_detail', kwargs={'slug': self.first.slug})
        response = self.client.post(url, {'quantity': '3'})
        self.assertRedirects(response, url)
        self.first.refresh_from_db()
        self.assertEqual(self.first.quantity, 3)

    def test_detail_database_failure_rolls_back_write(self):
        url = reverse('LCD:lcd_detail', kwargs={'slug': self.first.slug})
        before = self.stock_state()
        original_save = LCD.sell_lcd

        def fail_after_save(lcd, quantity):
            original_save(lcd, quantity)
            raise DatabaseError('Simulated write failure')

        with patch.object(LCD, 'sell_lcd', fail_after_save):
            with self.assertLogs('LCD.views', level='ERROR'):
                response = self.client.post(url, {'quantity': '3'}, follow=True)
        self.assertContains(response, 'هیچ تغییری ذخیره نشد')
        self.assertEqual(self.stock_state(), before)

    def test_maximum_supported_quantity_is_accepted(self):
        response = self.client.post(reverse('LCD:lcd_list'), {
            f'quantity_{self.first.slug}': '2147483647',
        })
        self.assertEqual(response.status_code, 302)
        self.first.refresh_from_db()
        self.assertEqual(self.first.quantity, 2147483647)

    def test_null_stock_renders_as_zero_in_bulk_inputs(self):
        self.first.quantity = None
        self.first.save()
        expected = f'name="quantity_{self.first.slug}" value="0" min="0"'
        for url in (reverse('LCD:lcd_list') + '?stock=zero', self.bulk_urls()[1]):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), expected)


class LinkParser(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.links = []
        self.rows = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs))
        elif tag == 'article' and dict(attrs).get('class') == 'lcd-row':
            self.rows.append(dict(attrs))


class LCDPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for index in range(45):
            LCD.objects.create(
                title=f'Available {index:02d}', quantity=1, buy_price=100, sell_price=150,
            )
        for index in range(25):
            LCD.objects.create(
                title=f'Empty {index:02d}', quantity=0, buy_price=100, sell_price=150,
            )
        cls.null_stock = LCD.objects.create(
            title='Null stock', quantity=None, buy_price=100, sell_price=150,
        )

    def list_url(self, **params):
        url = reverse('LCD:lcd_list')
        return f'{url}?{urlencode(params)}' if params else url

    def links(self, response):
        return LinkParser(response.content.decode()).links

    def test_all_available_products_are_reachable(self):
        seen = []
        for number, count in ((1, 20), (2, 20), (3, 5)):
            response = self.client.get(self.list_url(page=number))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context['lcd']), count)
            self.assertEqual(response.context['page_obj'].number, number)
            self.assertContains(response, 'aria-current="page"')
            seen.extend(lcd.pk for lcd in response.context['lcd'])
        self.assertEqual(len(set(seen)), 45)
        self.assertEqual(set(seen), set(LCD.objects.filter(quantity__gt=0).values_list('pk', flat=True)))

    def test_previous_and_next_links_at_boundaries(self):
        for number, has_previous, has_next in ((1, False, True), (2, True, True), (3, True, False)):
            with self.subTest(number=number):
                response = self.client.get(self.list_url(page=number))
                relations = {link.get('rel') for link in self.links(response)}
                self.assertEqual('prev' in relations, has_previous)
                self.assertEqual('next' in relations, has_next)

    def test_zero_stock_filter_is_applied_before_pagination(self):
        seen = []
        for number, count in ((1, 20), (2, 6)):
            response = self.client.get(self.list_url(stock='zero', page=number))
            self.assertEqual(response.context['paginator'].count, 26)
            self.assertEqual(len(response.context['lcd']), count)
            self.assertTrue(all(lcd.quantity in (0, None) for lcd in response.context['lcd']))
            rows = LinkParser(response.content.decode()).rows
            self.assertEqual(len(rows), count)
            self.assertTrue(all('hidden' not in row for row in rows))
            seen.extend(lcd.pk for lcd in response.context['lcd'])
        self.assertEqual(len(set(seen)), 26)
        self.assertIn(self.null_stock.pk, seen)

    def test_pagination_links_preserve_encoded_search_sort_and_stock(self):
        for index in range(21):
            LCD.objects.create(
                title=f'A&B + مدل {index}', quantity=0, buy_price=100, sell_price=150,
            )
        params = {'q': 'A&B + مدل', 'sort': '-buy_price', 'stock': 'zero', 'page': '1'}
        response = self.client.get(self.list_url(**params))
        next_link = next(link for link in self.links(response) if link.get('rel') == 'next')
        query = parse_qs(urlsplit(next_link['href']).query)
        self.assertEqual(query, {**{key: [value] for key, value in params.items()}, 'page': ['2']})
        next_response = self.client.get(reverse('LCD:lcd_list') + next_link['href'])
        self.assertEqual(next_response.context['paginator'].count, 21)
        self.assertEqual(len(next_response.context['lcd']), 1)

    def test_filter_and_sort_links_reset_page_and_preserve_search(self):
        response = self.client.get(self.list_url(q='Available', sort='quantity', page=2))
        links = self.links(response)
        stock_link = next(link for link in links if link.get('id') == 'lcd-stock-filter')
        self.assertEqual(parse_qs(urlsplit(stock_link['href']).query), {
            'q': ['Available'], 'sort': ['quantity'], 'stock': ['zero'],
        })
        for link in links:
            if link.get('class') == 'lcd-sort-link':
                query = parse_qs(urlsplit(link['href']).query)
                self.assertNotIn('page', query)
                self.assertEqual(query['q'], ['Available'])
        response = self.client.get(self.list_url(q='Empty', sort='quantity', stock='zero'))
        self.assertContains(response, 'name="stock" value="zero"')
        for link in self.links(response):
            if link.get('class') == 'lcd-sort-link':
                self.assertEqual(parse_qs(urlsplit(link['href']).query)['stock'], ['zero'])

    def test_equal_sort_values_have_stable_order_across_pages(self):
        expected = list(LCD.objects.filter(quantity__gt=0).order_by('buy_price', 'pk').values_list('pk', flat=True))
        actual = []
        for number in (1, 2, 3):
            response = self.client.get(self.list_url(sort='buy_price', page=number))
            actual.extend(lcd.pk for lcd in response.context['lcd'])
        self.assertEqual(actual, expected)

    def test_invalid_and_out_of_range_pages_are_safe(self):
        for requested, expected in (('abc', 1), ('0', 3), ('999', 3), ('last', 3)):
            with self.subTest(requested=requested):
                response = self.client.get(self.list_url(page=requested))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page_obj'].number, expected)

    def test_empty_and_single_page_results_do_not_show_navigation(self):
        for query, count in (('missing product', 0), ('Available 00', 1)):
            response = self.client.get(self.list_url(q=query, page=999))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['paginator'].count, count)
            self.assertNotContains(response, 'aria-label="صفحه‌بندی محصولات"')

    def test_bulk_save_stays_on_current_page_with_filters(self):
        url = self.list_url(q='Available', sort='buy_price', stock='available', page=2)
        product = self.client.get(url).context['lcd'][0]
        response = self.client.post(url, {f'quantity_{product.slug}': '8'}, follow=True)
        self.assertEqual(response.redirect_chain, [(url, 302)])
        self.assertEqual(response.context['page_obj'].number, 2)
        product.refresh_from_db()
        self.assertEqual(product.quantity, 8)

    def test_save_on_disappearing_last_page_falls_back_to_valid_page(self):
        url = self.list_url(sort='buy_price', stock='available', page=3)
        products = self.client.get(url).context['lcd']
        response = self.client.post(url, {
            f'quantity_{product.slug}': '0' for product in products
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(response.context['paginator'].count, 40)


class ModelSafetyTests(TestCase):
    def create_product(self, title, **kwargs):
        return LCD.objects.create(title=title, buy_price=100, sell_price=150, **kwargs)

    def create_record(self, model, title, **kwargs):
        if model is LCD:
            return self.create_product(title, **kwargs)
        return model.objects.create(title=title, **kwargs)

    def test_duplicate_titles_get_distinct_slugs(self):
        for model in (LCD, Brand):
            with self.subTest(model=model.__name__):
                records = [self.create_record(model, 'Same title') for _ in range(3)]
                self.assertEqual([record.slug for record in records], [
                    'same-title', 'same-title-2', 'same-title-3',
                ])

    def test_different_titles_that_normalize_to_same_slug_are_safe(self):
        for model in (LCD, Brand):
            with self.subTest(model=model.__name__):
                first = self.create_record(model, 'A & B')
                second = self.create_record(model, 'A B')
                self.assertNotEqual(first.slug, second.slug)
                self.assertEqual(first.slug, 'a-b')
                self.assertEqual(second.slug, 'a-b-2')

    def test_maximum_length_titles_and_suffixes_fit_slug_fields(self):
        for model in (LCD, Brand):
            with self.subTest(model=model.__name__):
                limit = model._meta.get_field('title').max_length
                records = [self.create_record(model, 'a' * limit) for _ in range(3)]
                self.assertEqual(len({record.slug for record in records}), 3)
                for record in records:
                    self.assertLessEqual(len(record.slug), model._meta.get_field('slug').max_length)
                    record.full_clean()

    def test_persian_titles_get_valid_unique_url_slugs(self):
        for model, detail_view in ((LCD, 'LCD:lcd_detail'), (Brand, 'LCD:brand_detail')):
            with self.subTest(model=model.__name__):
                records = [self.create_record(model, 'عنوان فارسی') for _ in range(2)]
                self.assertNotEqual(records[0].slug, records[1].slug)
                for record in records:
                    record.full_clean()
                    response = self.client.get(reverse(detail_view, kwargs={'slug': record.slug}))
                    self.assertEqual(response.status_code, 200)

    def test_existing_slugs_and_urls_survive_title_changes(self):
        for model, detail_view in ((LCD, 'LCD:lcd_detail'), (Brand, 'LCD:brand_detail')):
            with self.subTest(model=model.__name__):
                record = self.create_record(model, 'Original title', slug='existing-link')
                record.title = 'New title'
                record.save()
                record.refresh_from_db()
                self.assertEqual(record.slug, 'existing-link')
                self.assertEqual(self.client.get(reverse(detail_view, kwargs={
                    'slug': 'existing-link',
                })).status_code, 200)

    def test_missing_slug_is_saved_during_partial_updates(self):
        for model in (LCD, Brand):
            with self.subTest(model=model.__name__):
                record = self.create_record(model, 'Legacy title')
                model.objects.filter(pk=record.pk).update(slug=None)
                record.refresh_from_db()
                record.title = 'Updated title'
                record.save(update_fields=['title'])
                record.refresh_from_db()
                self.assertEqual(record.slug, 'updated-title')

    def test_slug_collision_during_save_is_retried_without_breaking_transaction(self):
        for model in (LCD, Brand):
            with self.subTest(model=model.__name__):
                existing = self.create_record(model, 'Claimed slug')
                original_generator = model._unique_slug
                calls = []

                def simulate_collision(record, using):
                    calls.append(record)
                    return existing.slug if len(calls) == 1 else original_generator(record, using)

                with patch.object(model, '_unique_slug', simulate_collision):
                    record = self.create_record(model, 'New record')
                self.assertEqual(len(calls), 2)
                self.assertNotEqual(record.slug, existing.slug)
                self.assertTrue(model.objects.filter(pk=record.pk).exists())

    def test_other_integrity_errors_are_not_hidden_or_retried(self):
        record = LCD(title='Invalid stock', buy_price=100, sell_price=150, quantity=-1)
        with patch.object(LCD, '_unique_slug', wraps=record._unique_slug) as generator:
            with self.assertRaises(IntegrityError):
                record.save()
        self.assertEqual(generator.call_count, 1)
        self.assertIsNone(record.slug)
        self.assertEqual(LCD.objects.count(), 0)

    def test_duplicate_titles_can_be_created_through_forms(self):
        for view, model, data in (
            ('LCD:lcd_create', LCD, {
                'title': 'Same product', 'quantity': 10, 'first_quantity': 10,
                'buy_price': 100, 'sell_price': 150,
            }),
            ('LCD:brand_create', Brand, {'title': 'Same brand'}),
        ):
            with self.subTest(view=view):
                for _ in range(2):
                    self.assertEqual(self.client.post(reverse(view), data).status_code, 302)
                records = list(model.objects.filter(title=data['title']))
                self.assertEqual(len(records), 2)
                self.assertEqual(len({record.slug for record in records}), 2)

    def test_deleting_used_brand_protects_products_and_brand(self):
        brand = Brand.objects.create(title='Used brand')
        product = self.create_product('Stock item', brand=brand, quantity=10)
        before = LCD.objects.values().get(pk=product.pk)
        for delete in (brand.delete, lambda: Brand.objects.filter(pk=brand.pk).delete()):
            with self.subTest(delete=delete):
                with self.assertRaises(ProtectedError):
                    delete()
                self.assertTrue(Brand.objects.filter(pk=brand.pk).exists())
                self.assertEqual(LCD.objects.values().get(pk=product.pk), before)

    def test_brand_can_be_deleted_after_product_is_detached(self):
        brand = Brand.objects.create(title='Detachable brand')
        product = self.create_product('Retained product', brand=brand, quantity=10)
        product.brand = None
        product.save(update_fields=['brand'])
        brand.delete()
        product.refresh_from_db()
        self.assertIsNone(product.brand)
        self.assertEqual(product.quantity, 10)

    def test_admin_explains_why_used_brand_cannot_be_deleted(self):
        brand = Brand.objects.create(title='Protected brand')
        product = self.create_product('Protected product', brand=brand)
        user = get_user_model().objects.create_superuser(
            username='admin', email='admin@example.com', password='test-password',
        )
        self.client.force_login(user)
        url = reverse('admin:LCD_brand_delete', args=[brand.pk])
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['protected'])
        self.assertTrue(Brand.objects.filter(pk=brand.pk).exists())
        self.assertTrue(LCD.objects.filter(pk=product.pk).exists())
