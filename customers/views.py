from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import administrative_role_required

from .forms import CustomerForm
from .models import Customer


@login_required
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customer_type = request.GET.get("type", "").strip()
    status = request.GET.get("status", "active").strip()
    customers = Customer.objects.select_related("created_by", "updated_by")

    if query:
        customers = customers.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(business_name__icontains=query)
            | Q(document_number__icontains=query)
            | Q(phone__icontains=query)
        )
    if customer_type in Customer.CustomerType.values:
        customers = customers.filter(customer_type=customer_type)
    if status == "active":
        customers = customers.filter(is_active=True)
    elif status == "inactive":
        customers = customers.filter(is_active=False)

    page_obj = Paginator(customers, 12).get_page(request.GET.get("page"))
    context = {
        "customers": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "selected_type": customer_type,
        "selected_status": status,
        "customer_types": Customer.CustomerType.choices,
        "can_edit": request.user.is_admin_role or request.user.role == "ADMINISTRATIVE",
        "total_customers": Customer.objects.count(),
        "active_customers": Customer.objects.filter(is_active=True).count(),
        "section": "customers",
    }
    return render(request, "customers/customer_list.html", context)


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(
        Customer.objects.select_related("created_by", "updated_by"), pk=pk
    )
    return render(
        request,
        "customers/customer_detail.html",
        {
            "customer": customer,
            "can_edit": request.user.is_admin_role or request.user.role == "ADMINISTRATIVE",
            "section": "customers",
        },
    )


@administrative_role_required
def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.updated_by = request.user
            customer.save()
            messages.success(request, f"Cliente {customer.display_name} registrado correctamente.")
            return redirect("customer_detail", pk=customer.pk)
    else:
        form = CustomerForm(initial={"is_active": True, "department": "Ica", "province": "Chincha"})
    return render(
        request,
        "customers/customer_form.html",
        {"form": form, "title": "Registrar cliente", "section": "customers"},
    )


@administrative_role_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(request, f"Datos de {updated.display_name} actualizados.")
            return redirect("customer_detail", pk=updated.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(
        request,
        "customers/customer_form.html",
        {"form": form, "title": f"Editar: {customer.display_name}", "customer": customer, "section": "customers"},
    )


@administrative_role_required
def customer_toggle_active(request, pk):
    if request.method != "POST":
        return redirect("customer_detail", pk=pk)
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = not customer.is_active
    customer.updated_by = request.user
    customer.save()
    state = "activado" if customer.is_active else "desactivado"
    messages.success(request, f"Cliente {customer.display_name} {state}.")
    return redirect("customer_detail", pk=customer.pk)
