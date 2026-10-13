from django import forms


class QuantityForm(forms.Form):
    def __init__(self, *args, min_value=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'] = forms.IntegerField(
            min_value=min_value,
            max_value=2147483647,
            error_messages={
                'required': 'تعداد را وارد کنید.',
                'invalid': 'تعداد باید عدد صحیح باشد.',
                'min_value': 'تعداد باید حداقل %(limit_value)s باشد.',
                'max_value': 'تعداد نباید بیشتر از %(limit_value)s باشد.',
            },
        )
