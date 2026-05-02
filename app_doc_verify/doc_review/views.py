import os
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q

from .models import DoctorApplication, Comment
from .email import send_decision_email


@login_required
def dashboard(request):
    qs = DoctorApplication.objects.all().order_by('-submitted_at')

    # --- filter & search ---
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if search_query:
        qs = qs.filter(
            Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
        )

    counts = {
        'pending': DoctorApplication.objects.filter(status='pending').count(),
        'approved': DoctorApplication.objects.filter(status='approved').count(),
        'rejected': DoctorApplication.objects.filter(status='rejected').count(),
    }

    # --- pagination ---
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- which applications have comments (for yellow dot) ---
    commented_ids = set(
        Comment.objects.values_list('application_id', flat=True).distinct()
    )

    return render(request, 'doc_review/dashboard.html', {
        'page_obj': page_obj,
        'counts': counts,
        'status_filter': status_filter,
        'search_query': search_query,
        'commented_ids': commented_ids,
    })


@login_required
def application_detail(request, pk):
    application = get_object_or_404(DoctorApplication, pk=pk)

    # handle new comment POST
    if request.method == 'POST':
        text = request.POST.get('comment_text', '').strip()
        if text:
            Comment.objects.create(
                application=application,
                author=request.user,
                text=text,
            )
        return redirect('application_detail', pk=pk)

    # build doc file list
    folder_path = os.path.join(settings.MEDIA_ROOT, application.doc_folder)
    doc_files = []
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            doc_files.append({
                'name': filename,
                'url': f"{settings.MEDIA_URL}{application.doc_folder}/{filename}",
            })

    comments = application.comments.select_related('author').order_by('created_at')

    return render(request, 'doc_review/application_detail.html', {
        'application': application,
        'doc_files': doc_files,
        'comments': comments,
    })


@login_required
def review_application(request, pk):
    if request.method != 'POST':
        return redirect('application_detail', pk=pk)

    application = get_object_or_404(DoctorApplication, pk=pk)
    action = request.POST.get('action')

    if action == 'approve':
        application.status = DoctorApplication.STATUS_APPROVED
        application.rejection_reason = ''
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()
        send_decision_email(application)
        messages.success(request, f"{application.full_name}'s application has been approved.")

    elif action == 'reject':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('application_detail', pk=pk)
        application.status = DoctorApplication.STATUS_REJECTED
        application.rejection_reason = reason
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()
        send_decision_email(application)
        messages.success(request, f"{application.full_name}'s application has been rejected.")

    return redirect('dashboard')


@login_required
def bulk_action(request):
    if request.method != 'POST':
        return redirect('dashboard')

    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')

    if not selected_ids:
        messages.error(request, 'No applications selected.')
        return redirect('dashboard')

    applications = DoctorApplication.objects.filter(pk__in=selected_ids, status='pending')

    if action == 'bulk_approve':
        for app in applications:
            app.status = DoctorApplication.STATUS_APPROVED
            app.rejection_reason = ''
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()
            send_decision_email(app)
        messages.success(request, f"{applications.count()} application(s) approved.")

    elif action == 'bulk_reject':
        reason = request.POST.get('bulk_rejection_reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason for bulk rejection.')
            return redirect('dashboard')
        for app in applications:
            app.status = DoctorApplication.STATUS_REJECTED
            app.rejection_reason = reason
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()
            send_decision_email(app)
        messages.success(request, f"{applications.count()} application(s) rejected.")

    return redirect('dashboard')


@login_required
def all_comments(request):
    comments = Comment.objects.select_related('application', 'author').order_by('-created_at')
    return render(request, 'doc_review/all_comments.html', {'comments': comments})


@login_required
def export_csv(request):
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')

    qs = DoctorApplication.objects.all().order_by('-submitted_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if search_query:
        qs = qs.filter(
            Q(full_name__icontains=search_query) | Q(email__icontains=search_query)
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="applications.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Specialization', 'Status', 'Rejection Reason', 'Reviewed By', 'Reviewed At', 'Submitted At'])

    for app in qs:
        writer.writerow([
            app.pk,
            app.full_name,
            app.email,
            app.phone,
            app.specialization,
            app.get_status_display(),
            app.rejection_reason,
            app.reviewed_by.username if app.reviewed_by else '',
            app.reviewed_at.strftime('%d %b %Y %H:%M') if app.reviewed_at else '',
            app.submitted_at.strftime('%d %b %Y %H:%M'),
        ])

    return response


def logout_view(request):
    auth_logout(request)
    return redirect('home')
