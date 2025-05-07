from django.contrib import admin
from .models import Drug, Prescription

@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock_quantity', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')
    ordering = ('name',)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('medication_name', 'doctor', 'patient', 'status', 'prescribed_at', 'updated_at')
    list_filter = ('status', 'prescribed_at')
    search_fields = ('medication_name', 'doctor__username', 'patient__username')
    autocomplete_fields = ('doctor', 'patient')
    ordering = ('-prescribed_at',)
