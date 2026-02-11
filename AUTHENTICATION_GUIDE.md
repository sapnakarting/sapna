# Authentication System - Quick Reference Guide

## Architecture Overview
```
User (Django) → UserProfile (Role: ADMIN/FUEL_AGENT)
    ↓
LoginView → authenticate() → login()
    ↓
Permission Decorators → Check role
    ↓
Views → Protected resources
```

## Role Definitions

### ADMIN
- Full system access
- User management (CRUD)
- All fleet operations
- Settings and configuration

### FUEL_AGENT
- Limited operations access
- Fuel log entry
- View assigned vehicles/drivers
- No user management

## Using Permission Decorators

```python
from fleet.utils.permissions import is_admin_required, is_fuel_agent_required, any_role_required

# Admin only
@is_admin_required
def admin_view(request):
    # Only ADMIN role can access
    pass

# Admin or Fuel Agent
@is_fuel_agent_required
def protected_view(request):
    # Both ADMIN and FUEL_AGENT can access
    pass

# Same as @is_fuel_agent_required
@any_role_required
def common_view(request):
    # Both ADMIN and FUEL_AGENT can access
    pass
```

## Checking User Roles in Templates

```html
{% if user.is_authenticated %}
    {% if user.userprofile.is_admin %}
        <!-- Admin-specific content -->
        <a href="{% url 'fleet:user-list' %}">Manage Users</a>
    {% endif %}

    {% if user.userprofile.is_fuel_agent %}
        <!-- Fuel Agent-specific content -->
        <a href="{% url 'fleet:fuel-log-add' %}">Add Fuel Log</a>
    {% endif %}
{% endif %}
```

## Checking User Roles in Views

```python
def my_view(request):
    if request.user.userprofile.is_admin():
        # Admin logic
        pass
    elif request.user.userprofile.is_fuel_agent():
        # Fuel agent logic
        pass
```

## URL Patterns

### Authentication
- `/login/` - Login page
- `/logout/` - Logout (POST only)

### User Management (Admin Only)
- `/fleet/users/` - List all users
- `/fleet/users/create/` - Create new user
- `/fleet/users/<id>/edit/` - Edit user
- `/fleet/users/<id>/delete/` - Delete user

## Form Usage

### Login Form
```python
from fleet.forms import LoginForm

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            # Login logic handled by LoginView
```

### User Creation Form
```python
from fleet.forms import UserCreationForm

def create_user_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # UserProfile is created automatically
            # Role is set from form.cleaned_data['role']
```

## User Profile Access

```python
# Get user profile
user = request.user
profile = user.userprofile

# Check role
if profile.role == 'ADMIN':
    # Admin access
elif profile.role == 'FUEL_AGENT':
    # Fuel agent access

# Helper methods
profile.is_admin()  # Returns True/False
profile.is_fuel_agent()  # Returns True/False
```

## Creating Users Programmatically

```python
from django.contrib.auth.models import User
from fleet.models import UserProfile

# Create user with profile
user = User.objects.create_user(
    username='johndoe',
    email='john@example.com',
    password='securepassword'
)

# Create profile
profile = UserProfile.objects.create(
    user=user,
    role='FUEL_AGENT',
    phone='+1234567890'
)
```

## Common Patterns

### Protecting a View by Role
```python
from fleet.utils.permissions import is_admin_required

@is_admin_required
def delete_item(request, item_id):
    # Only admin can delete
    item = get_object_or_404(Item, id=item_id)
    item.delete()
    return redirect('item-list')
```

### Filtering Data by Role
```python
def list_items(request):
    queryset = Item.objects.all()

    if request.user.userprofile.is_fuel_agent():
        # Fuel agents can only see their assigned items
        queryset = queryset.filter(assigned_to=request.user)

    # Admin can see everything
    return render(request, 'items/list.html', {'items': queryset})
```

### Role-Based Redirects
```python
def process_login(request):
    user = authenticate(request, username=username, password=password)

    if user:
        login(request, user)

        if user.userprofile.is_admin():
            return redirect('admin-dashboard')
        elif user.userprofile.is_fuel_agent():
            return redirect('agent-dashboard')
```

## Error Handling

### User Without Profile
```python
# Automatically handled by signals
# UserProfile is created when User is created

# Manual check if needed
if not hasattr(user, 'userprofile'):
    UserProfile.objects.create(user=user, role='FUEL_AGENT')
```

### Invalid Role Access
```python
# Permission decorators automatically redirect to dashboard
# No need to handle in views

# Custom handling:
if not request.user.userprofile.is_admin():
    messages.error(request, 'Access denied')
    return redirect('dashboard')
```

## Testing

### Create Test Users
```bash
python manage.py create_default_users
```

### Test Login
```bash
# Admin
Username: admin
Password: admin123

# Fuel Agent
Username: fuel_agent
Password: fuel123
```

## Troubleshooting

### User can't log in
1. Check if UserProfile exists: `user.userprofile`
2. Verify user is active: `user.is_active`
3. Check password is correct
4. Verify role is set: `user.userprofile.role`

### Permission denied
1. Check user role: `request.user.userprofile.role`
2. Verify decorator is correct for the role
3. Ensure UserProfile exists for the user

### Auto-profile not created
1. Check if signals are loaded (apps.py ready method)
2. Verify fleet app is in INSTALLED_APPS
3. Restart server after adding signals

## Security Notes

- All passwords are hashed by Django
- CSRF protection enabled on all forms
- Logout requires POST to prevent CSRF
- Session expiration: 24 hours (configurable)
- Profile checks prevent privilege escalation

## Next Steps

1. Run migrations: `python manage.py makemigrations && python manage.py migrate`
2. Create default users: `python manage.py create_default_users`
3. Test login at: http://127.0.0.1:8000/login/
4. Access admin panel: http://127.0.0.1:8000/admin/
