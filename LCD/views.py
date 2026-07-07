from django.db.models import Q
from django.shortcuts import render, redirect
from django.views.generic import DetailView, ListView,CreateView,UpdateView,DeleteView
from django.urls import reverse_lazy
from LCD.models import LCD, Brand, Wallet
from django.db.models import Sum

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

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return LCD.objects.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        return LCD.objects.all()

    def get_context_data(self, **kwargs):
        total_quantity = LCD.objects.aggregate(total=Sum('quantity'))['total'] or 0
        context = super().get_context_data(**kwargs)
        context['wallet'] = Wallet.objects.first()
        context['total_quantity'] = total_quantity
        return context

    def post(self, request, *args, **kwargs):
        print(request.POST)
        print(request.POST.get("lcd_slug"))
        lcd_slug = request.POST.get('lcd_slug')
        quantity = int(request.POST.get('quantity'))
        lcd = LCD.objects.get(slug=lcd_slug)
        lcd.sell_lcd(quantity)
        return redirect('LCD:lcd_list')



class LCDCreateView(CreateView):
    model = LCD
    fields = '__all__'
    context_object_name = 'lcd'
    template_name = 'LCD_template/lcd_create.html'
    success_url = reverse_lazy('LCD:lcd_list')


    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(LCDCreateView, self).form_valid(form)


class LCDUpdateView(UpdateView):
    model = LCD
    fields = '__all__'
    context_object_name = 'lcd'
    template_name = 'LCD_template/lcd_update.html'

    def get_success_url(self):
        return reverse_lazy('LCD:lcd_detail', kwargs={'slug': self.object.slug})


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lcd'] = self.object.lcd.all()
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