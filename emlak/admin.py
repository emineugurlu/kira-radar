# emlak/admin.py
from django.contrib import admin
from .models import Bolge, KiraIlani

# Bolge modelini admin paneline kaydet
@admin.register(Bolge)
class BolgeAdmin(admin.ModelAdmin):
    list_display = ('sehir', 'ilce', 'mahalle', 'ortalama_kira', 'son_artis_yuzdesi')
    search_fields = ('sehir', 'ilce', 'mahalle')
    list_filter = ('sehir', 'ilce')

# KiraIlani modelini admin paneline kaydet
@admin.register(KiraIlani)
class KiraIlaniAdmin(admin.ModelAdmin):
    list_display = ('fiyat', 'bolge', 'metrekare', 'ilan_tarihi', 'ilan_kaynagi', 'veri_cekme_tarihi')
    list_filter = ('ilan_kaynagi', 'ilan_tarihi', 'bolge__sehir', 'bolge__ilce', 'esyalimi')
    search_fields = ('aciklama', 'ilan_url')
    raw_id_fields = ('bolge',)