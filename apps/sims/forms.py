from django import forms
from apps.sims.models import Sims

class addSims(forms.Form):
    # class meta:
    #     model = Sims
    #     fields = ['sim', 'type_sim', 'operator']
        
    type_sim = forms.CharField()
    operator = forms.CharField()
    sim = forms.FileField()

SIM_OPERATOR = [
    ('TM', 'T-Mobile'), 
    ('CM', 'China Mobile'),
    ('TC', 'Telcom')
]

SIM_TYPES = [
    ('sim', 'SIM (Físico)'),   
    ('esim', 'eSIM (Virtual)')  
]


class AddSimsForm(forms.Form):  
    sim=forms.CharField(
        label='Nome de Login',
        required=True, 
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: 8901000000000000000F',
            }
        )
    )
    type_sim=forms.CharField(
        label='Tipo de SIM',
        widget=forms.RadioSelect(
            attrs={
                'class': 'form-control'
            },
            choices=SIM_TYPES,
        )
    )
    operator=forms.CharField(
        label='Operadoras',
        widget=forms.RadioSelect(
            attrs={
                'class': 'form-control'
            },
            choices=SIM_OPERATOR,
        )
    )
