from django.db import models

class Bolge(models.Model):
    # Şehir, ilçe, mahalle gibi konum bilgileri
    sehir = models.CharField(max_length=100, verbose_name="Şehir")
    ilce = models.CharField(max_length=100, verbose_name="İlçe")
    mahalle = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mahalle") # Mahalle boş olabilir

    # Harita görselleştirmesi için coğrafi bilgiler (Opsiyonel ama önemli)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Enlem")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Boylam")

    # Fahiş artış tespiti için ortalama kira fiyatı veya son artış yüzdesi gibi alanlar eklenebilir
    ortalama_kira = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Ortalama Kira")
    son_artis_yuzdesi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Son Artış Yüzdesi")

    class Meta:
        verbose_name = "Bölge"
        verbose_name_plural = "Bölgeler"
        unique_together = (('sehir', 'ilce', 'mahalle'),) # Şehir, ilçe, mahalle kombinasyonu tekil olmalı

    def __str__(self):
        if self.mahalle:
            return f"{self.mahalle}, {self.ilce}, {self.sehir}"
        return f"{self.ilce}, {self.sehir}"

class KiraIlani(models.Model):
    # İlanın ait olduğu bölge
    bolge = models.ForeignKey(Bolge, on_delete=models.CASCADE, related_name='kira_ilanlari', verbose_name="Bölge")

    # İlanın temel bilgileri
    fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Kira Fiyatı")
    metrekare = models.IntegerField(verbose_name="Metrekare")
    oda_sayisi = models.CharField(max_length=50, blank=True, null=True, verbose_name="Oda Sayısı") # 1+1, 2+1 gibi
    binanin_yasi = models.IntegerField(blank=True, null=True, verbose_name="Binanın Yaşı")
    esyalimi = models.BooleanField(default=False, verbose_name="Eşyalı mı?")
    isinma_tipi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Isınma Tipi")

    # İlana özel bilgiler
    ilan_url = models.URLField(max_length=500, unique=True, verbose_name="İlan URL'si") # İlan URL'si tekil olmalı
    ilan_kaynagi = models.CharField(max_length=100, verbose_name="İlan Kaynağı") # Sahibinden, Emlakjet vb.
    ilan_tarihi = models.DateField(verbose_name="İlan Tarihi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    # scraping tarihi
    veri_cekme_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Veri Çekme Tarihi")

    class Meta:
        verbose_name = "Kira İlanı"
        verbose_name_plural = "Kira İlanları"
        ordering = ['-ilan_tarihi'] # Varsayılan olarak ilan tarihine göre tersten sırala

    def __str__(self):
        return f"{self.fiyat} TL - {self.bolge} - {self.ilan_kaynagi}"