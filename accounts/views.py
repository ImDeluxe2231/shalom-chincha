from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_role_required
from .forms import ProfileForm, UserCreateForm, UserUpdateForm
from .models import User


@login_required
def dashboard(request):
    from reports.services import build_dashboard_context

    context = build_dashboard_context(request.GET, request.user)
    context["section"] = "dashboard"
    if request.user.is_admin_role:
        context.update(
            {
                "total_users": User.objects.count(),
                "active_users": User.objects.filter(is_active=True).count(),
                "admin_users": User.objects.filter(role=User.Role.ADMIN).count(),
                "operational_users": User.objects.filter(role=User.Role.OPERATIONAL).count(),
                "recent_users": User.objects.order_by("-date_joined")[:5],
            }
        )
    return render(request, "accounts/dashboard.html", context)


@admin_role_required
def user_list(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    users = User.objects.all()
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(document_number__icontains=query)
        )
    if role in User.Role.values:
        users = users.filter(role=role)
    return render(
        request,
        "accounts/user_list.html",
        {"users": users, "query": query, "selected_role": role, "roles": User.Role.choices, "section": "users"},
    )


@admin_role_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.created_by = request.user
            user.save()
            messages.success(request, f"Usuario {user.username} creado correctamente.")
            return redirect("user_list")
    else:
        form = UserCreateForm(initial={"is_active": True})
    return render(request, "accounts/user_form.html", {"form": form, "title": "Nuevo usuario", "section": "users"})


@admin_role_required
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated == request.user and not updated.is_active:
                form.add_error("is_active", "No puedes desactivar tu propia cuenta.")
            else:
                updated.save()
                messages.success(request, f"Usuario {updated.username} actualizado.")
                return redirect("user_list")
    else:
        form = UserUpdateForm(instance=user)
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "title": f"Editar usuario: {user.username}", "editing_user": user, "section": "users"},
    )


@admin_role_required
def user_toggle_active(request, pk):
    if request.method != "POST":
        return redirect("user_list")
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "No puedes desactivar tu propia cuenta.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active", "updated_at"])
        state = "activado" if user.is_active else "desactivado"
        messages.success(request, f"Usuario {user.username} {state}.")
    return redirect("user_list")


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form, "section": "profile"})
