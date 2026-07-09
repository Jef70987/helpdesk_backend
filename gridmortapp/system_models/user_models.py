from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Department(models.Model):
    """Departments within the organization"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class EmployeeProfile(models.Model):
    """Extended user profile for employees"""
    USER_TYPES = (
        ('employee', 'Employee'),
        ('it_staff', 'IT Staff'),
        ('manager', 'Manager'),
        ('admin', 'Administrator'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='employee')
    
    # Contact information
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    office_location = models.CharField(max_length=100, blank=True, null=True)
    
    # Employment details
    hire_date = models.DateField(null=True, blank=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    
    # System access
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email


# Signal to automatically create EmployeeProfile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        EmployeeProfile.objects.create(
            user=instance,
            employee_id=f"EMP-{instance.id:05d}"
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()