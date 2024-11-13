from django.contrib import admin


class BasePermissionsAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        if request.user.is_staff:
            return True
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_view_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        return False
