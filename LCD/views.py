from django.db.models import Q
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView,CreateView,UpdateView,DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse
from LCD.models import LCD, Brand, Wallet
from django.db.models import Sum
import openpyxl

class LCDDetailView(DetailView):
    model = LCD
    context_object_name = 'lcd'
    template_name = 'LCD_template/LCD_detail.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        quantity = int(self.request.POST.get('quantity'))
        self.object.sell_lcd(quantity)
        return redirect('LCD:lcd_detail', slug=self.object.slug)


class LCDListView(ListView):
    model = LCD
    context_object_name = 'lcd'
    template_name = 'LCD_template/LCD_list_template.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = {
            'quantity': 'quantity',
            '-quantity': '-quantity',
            'buy_price': 'buy_price',
            '-buy_price': '-buy_price',
        }
        order = valid_sorts.get(sort, '-created_at')
        qs = LCD.objects.all()
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        return qs.order_by(order)

    def get_context_data(self, **kwargs):
        total_quantity = LCD.objects.aggregate(total=Sum('quantity'))['total'] or 0
        context = super().get_context_data(**kwargs)
        context['wallet'] = Wallet.objects.first()
        context['total_quantity'] = total_quantity
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        context['current_q'] = self.request.GET.get('q', '')
        return context

    def post(self, request, *args, **kwargs):
        # print(request.POST)
        # print(request.POST.get("lcd_slug"))
        # lcd_slug = request.POST.get('lcd_slug')
        for lcd in LCD.objects.all():
            quantity = (request.POST.get(f'quantity_{lcd.slug}'))
            if quantity :
                lcd.sell_lcd(int(quantity))
        return redirect('LCD:lcd_list')



class LCDCreateView(CreateView):
    model = LCD
    fields = ['title', 'brand', 'quantity', 'first_quantity', 'sell_price', 'buy_price']
    context_object_name = 'lcd'
    template_name = 'LCD_template/lcd_create.html'
    success_url = reverse_lazy('LCD:lcd_list')


    def form_valid(self, form):
        return super(LCDCreateView, self).form_valid(form)


class LCDUpdateView(UpdateView):
    model = LCD
    fields = ['title', 'brand', 'quantity', 'first_quantity', 'sell_price', 'buy_price']
    context_object_name = 'lcd'
    template_name = 'LCD_template/lcd_update.html'
    success_url = reverse_lazy('LCD:lcd_list')
    # def get_success_url(self):
    #     return reverse_lazy('LCD:lcd_detail', kwargs={'slug': self.object.slug})


class LCDDeleteView(DeleteView):
    model = LCD
    success_url = reverse_lazy('LCD:lcd_list')
    template_name = 'LCD_template/delete_lcd.html'

class BrandDetailView(DetailView):
    model = Brand
    context_object_name = 'brand'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    template_name = 'LCD_template/brand.html'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        for lcd in self.object.lcd.all():
            quantity = request.POST.get(f'quantity_{lcd.slug}')
            if quantity:
                lcd.sell_lcd(int(quantity))
        return redirect('LCD:brand_detail', slug=self.object.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = {
            'quantity': 'quantity',
            '-quantity': '-quantity',
            'buy_price': 'buy_price',
            '-buy_price': '-buy_price',
        }
        order = valid_sorts.get(sort, '-created_at')
        context['lcd'] = self.object.lcd.all().order_by(order)
        context['current_sort'] = sort
        return context


class BrandListView(ListView):
    model = Brand
    context_object_name = 'brand'
    template_name = 'LCD_template/brand_list.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Brand.objects.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        return Brand.objects.all()


class BrandCreateView(CreateView):
    model = Brand
    fields = ['title']
    context_object_name = 'brand'
    template_name = 'LCD_template/brand_create.html'
    success_url = reverse_lazy('LCD:brand_list')


class BrandUpdateView(UpdateView):
    model = Brand
    fields = ['title']
    context_object_name = 'brand'
    template_name = 'LCD_template/brand_update.html'
    def get_success_url(self):
        return reverse_lazy('LCD:brand_detail', kwargs={'slug': self.object.slug})



class WalletBalanceUpdateView(UpdateView):
    model = Wallet
    fields = ['balance']
    context_object_name = 'wallet'
    success_url = reverse_lazy('LCD:lcd_list')
    template_name = 'LCD/wallet_form.html'


def export_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LCD"

    headers = ['عنوان', 'برند', 'موجودی', 'قیمت خرید', 'قیمت فروش', 'موجودی اولیه', 'اسلاگ', 'آخرین بروزرسانی']
    ws.append(headers)

    for lcd in LCD.objects.all().iterator():
        ws.append([
            lcd.title,
            str(lcd.brand) if lcd.brand else '',
            lcd.quantity or 0,
            lcd.buy_price,
            lcd.sell_price,
            lcd.first_quantity or 0,
            lcd.slug or '',
            lcd.updated_at.strftime('%Y-%m-%d %H:%M') if lcd.updated_at else '',
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="lcd_inventory.xlsx"'
    wb.save(response)
    return response
