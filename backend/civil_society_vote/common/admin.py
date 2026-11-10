from django.contrib import admin


class BasePermissionsAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return bool(request.user.is_staff)

    def has_add_permission(self, request):
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_staff)
