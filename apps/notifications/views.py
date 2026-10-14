from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notif = generics.get_object_or_404(Notification.objects.filter(recipient=request.user), pk=pk)
        notif.is_read = True
        notif.save(update_fields=['is_read', 'updated_at'])
        return Response({'success': True})

class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'success': True})
