# emlak/management/commands/maliyet_hesapla.py

from django.core.management.base import BaseCommand
from emlak.models import KiraIlani, Bolge
from django.db.models import Avg, Count
from django.db.models.functions import TruncMonth
from datetime import timedelta
from django.utils import timezone
import traceback # Hata ayıklama için ekledik

class Command(BaseCommand):
    help = 'Belirli bir bölge (ilçe veya mahalle) için kira maliyet analizi yapar.'

    def add_arguments(self, parser):
        # Tüm argümanları anahtarlı yapıyoruz
        parser.add_argument('--sehir', type=str, required=True, help='Analiz edilecek şehrin adı (örn: İstanbul)')
        parser.add_argument('--ilce', type=str, required=True, help='Analiz edilecek ilçenin adı (örn: Kadıköy)')
        parser.add_argument('--mahalle', type=str, default=None,
                            help='Opsiyonel: Analiz edilecek mahallenin adı (örn: Caddebostan)')

    def handle(self, *args, **options):
        # Argümanlara options sözlüğü üzerinden erişim
        sehir_adi = options['sehir']
        ilce_adi = options['ilce']
        mahalle_adi = options['mahalle']

        if mahalle_adi:
            self.stdout.write(self.style.SUCCESS(f'{mahalle_adi}, {ilce_adi}, {sehir_adi} için kira maliyet analizi başlatılıyor...'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{ilce_adi}, {sehir_adi} için kira maliyet analizi başlatılıyor...'))

        try:
            bolge_filtresi = {
                'sehir__iexact': sehir_adi,
                'ilce__iexact': ilce_adi
            }
            if mahalle_adi:
                bolge_filtresi['mahalle__iexact'] = mahalle_adi

            ilgili_bolgeler = Bolge.objects.filter(**bolge_filtresi)

            if not ilgili_bolgeler.exists():
                self.stdout.write(self.style.WARNING(f"Belirtilen bölge için (Şehir: {sehir_adi}, İlçe: {ilce_adi}, Mahalle: {mahalle_adi or 'Tümü'}) veritabanında bölge kaydı bulunamadı."))
                self.stdout.write(self.style.NOTICE("Lütfen önce Bolge modelinize ilgili kayıtları eklediğinizden veya scraping ile oluştuğundan emin olun."))
                return

            kira_ilanlari = KiraIlani.objects.filter(bolge__in=ilgili_bolgeler)

            if not kira_ilanlari.exists():
                self.stdout.write(self.style.WARNING(f"Belirtilen bölge için (Şehir: {sehir_adi}, İlçe: {ilce_adi}, Mahalle: {mahalle_adi or 'Tümü'}) veritabanında kira ilanı bulunamadı."))
                self.stdout.write(self.style.NOTICE("Lütfen veri çektiğinizden ve ilanların doğru bölgelerle ilişkilendirildiğinden emin olun."))
                return

            ortalama_kira = kira_ilanlari.aggregate(Avg('fiyat'))['fiyat__avg']

            if ortalama_kira is not None:
                mesaj_baslik = f"'{mahalle_adi}, {ilce_adi}, {sehir_adi}'" if mahalle_adi else f"'{ilce_adi}, {sehir_adi}'"
                self.stdout.write(self.style.SUCCESS(f"{mesaj_baslik} bölgesindeki ortalama kira: {ortalama_kira:.2f} TL"))
                self.stdout.write(self.style.NOTICE(f"Toplam {kira_ilanlari.count()} adet ilan üzerinden hesaplanmıştır."))

                self.stdout.write(self.style.HTTP_INFO("\n--- Daha Detaylı Analizler ---"))

                uc_ay_once = timezone.now() - timedelta(days=90)
                son_uc_aylik_ilanlar = kira_ilanlari.filter(ilan_tarihi__gte=uc_ay_once)

                if son_uc_aylik_ilanlar.count() > 0:
                    aylik_ortalama = son_uc_aylik_ilanlar.annotate(
                        month=TruncMonth('ilan_tarihi')
                    ).values('month').annotate(
                        avg_fiyat=Avg('fiyat')
                    ).order_by('month')

                    self.stdout.write(self.style.NOTICE("Son 3 Ayın Ortalama Kira Fiyatları:"))
                    for entry in aylik_ortalama:
                        self.stdout.write(self.style.NOTICE(f"  {entry['month'].strftime('%Y-%m')}: {entry['avg_fiyat']:.2f} TL"))
                else:
                    self.stdout.write(self.style.WARNING("Son 3 ay için yeterli ilan verisi bulunamadı."))

                if ilgili_bolgeler.first().ortalama_kira and ortalama_kira > ilgili_bolgeler.first().ortalama_kira * 1.20:
                    self.stdout.write(self.style.ERROR("UYARI: Bu bölgede fahiş kira artışı potansiyeli tespit edildi!"))
                elif ilgili_bolgeler.first().ortalama_kira and ortalama_kira > ilgili_bolgeler.first().ortalama_kira * 1.10:
                     self.stdout.write(self.style.WARNING("Bu bölgede kira artışı mevcut, takipte kalın."))
                else:
                    self.stdout.write(self.style.SUCCESS("Bu bölgedeki kira artışı normal seviyelerde görünüyor."))

            else:
                self.stdout.write(self.style.WARNING(f"'{ilce_adi}, {sehir_adi}' için ortalama kira hesaplanamadı."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Maliyet analizi sırasında beklenmedik bir hata oluştu: {e}"))
            self.stdout.write(self.style.ERROR(traceback.format_exc())) # Detaylı hata çıktısı

        if mahalle_adi:
            self.stdout.write(self.style.SUCCESS(f'{mahalle_adi}, {ilce_adi}, {sehir_adi} için kira maliyet analizi tamamlandı!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{ilce_adi}, {sehir_adi} için kira maliyet analizi tamamlandı!'))