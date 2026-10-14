from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from apps.accounts.models import User, OrganizationMembership, AuthToken
from apps.accounts.serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    OrganizationMembershipSerializer, SwitchOrganizationSerializer,
    InviteEmployeeSerializer, VerifyTokenSerializer, SetPasswordSerializer
)
from apps.accounts.services import create_user_and_organization

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(email=data['email'].lower()).exists():
            return Response({'error': {'message': 'A user with this email already exists.'}}, status=status.HTTP_400_BAD_REQUEST)

        user, org, membership, token = create_user_and_organization(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            company_name=data['company_name']
        )

        return Response({
            'success': True,
            'token': token.key,
            'user': UserSerializer(user).data,
            'organization': {
                'id': str(org.id),
                'name': org.name,
                'slug': org.slug,
                'role': membership.role,
            }
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data['email'].lower()
        password = data['password']

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': {'message': 'Invalid email or password.'}}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'error': {'message': 'This account has been deactivated.'}}, status=status.HTTP_403_FORBIDDEN)

        # Create or fetch AuthToken
        token, _ = AuthToken.objects.get_or_create(user=user)

        memberships = OrganizationMembership.objects.filter(user=user, is_active=True).select_related('organization')
        memberships_data = OrganizationMembershipSerializer(memberships, many=True).data

        active_membership = memberships.first()
        active_org = {
            'id': str(active_membership.organization.id),
            'name': active_membership.organization.name,
            'slug': active_membership.organization.slug,
            'role': active_membership.role,
        } if active_membership else None

        return Response({
            'success': True,
            'token': token.key,
            'user': UserSerializer(user).data,
            'active_organization': active_org,
            'organizations': memberships_data,
        })

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if hasattr(request, 'auth') and isinstance(request.auth, AuthToken):
            request.auth.delete()
        logout(request)
        return Response({'success': True, 'message': 'Logged out successfully.'})

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        memberships = OrganizationMembership.objects.filter(user=request.user, is_active=True).select_related('organization')
        memberships_data = OrganizationMembershipSerializer(memberships, many=True).data

        active_org_data = None
        if getattr(request, 'organization', None) and getattr(request, 'organization_membership', None):
            active_org_data = {
                'id': str(request.organization.id),
                'name': request.organization.name,
                'slug': request.organization.slug,
                'role': request.organization_membership.role,
                'onboarding_completed': request.organization.onboarding_completed,
                'onboarding_step': request.organization.onboarding_step,
            }

        # Check if user has an associated Employee record in this organization
        employee_data = None
        if active_org_data:
            from apps.employees.models import Employee
            employee = Employee.objects.filter(organization=request.organization, user=request.user).first()
            if employee:
                employee_data = {
                    'id': str(employee.id),
                    'employee_code': employee.employee_code,
                    'designation': employee.designation,
                }

        return Response({
            'user': UserSerializer(request.user).data,
            'active_organization': active_org_data,
            'organizations': memberships_data,
            'employee': employee_data,
        })

class SwitchOrganizationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SwitchOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_org_id = serializer.validated_data['organization_id']

        membership = OrganizationMembership.objects.filter(
            user=request.user,
            organization_id=target_org_id,
            is_active=True
        ).select_related('organization').first()

        if not membership:
            return Response(
                {'error': {'message': 'You are not an authorized member of this organization.'}},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'success': True,
            'active_organization': {
                'id': str(membership.organization.id),
                'name': membership.organization.name,
                'slug': membership.organization.slug,
                'role': membership.role,
                'onboarding_completed': membership.organization.onboarding_completed,
            }
        })


class InviteEmployeeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.employees.models import Employee
        from apps.accounts.services import send_employee_invitation

        if not request.organization:
            return Response({'error': {'message': 'Organization context required.'}}, status=status.HTTP_400_BAD_REQUEST)

        if not request.organization_membership or request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            return Response({'error': {'message': 'Only Organization Owners and HR Admins can send invitations.'}}, status=status.HTTP_403_FORBIDDEN)

        serializer = InviteEmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emp_id = serializer.validated_data['employee_id']

        employee = Employee.objects.filter(organization=request.organization, id=emp_id).first()
        if not employee:
            return Response({'error': {'message': 'Employee not found in your organization.'}}, status=status.HTTP_404_NOT_FOUND)

        if not employee.user:
            return Response({'error': {'message': 'No user account linked to this employee.'}}, status=status.HTTP_400_BAD_REQUEST)

        activation_url, uid, token = send_employee_invitation(employee, request)

        return Response({
            'success': True,
            'message': f'Activation invitation sent to {employee.email}.',
            'activation_url': activation_url,
            'recipient': employee.email,
        })


class VerifyActivationTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')
        if not uid or not token:
            return Response({'error': {'message': 'Missing uid or token parameter.'}}, status=status.HTTP_400_BAD_REQUEST)

        from apps.accounts.services import verify_invitation_token
        user, error = verify_invitation_token(uid, token)
        if error:
            return Response({'error': {'message': error}}, status=status.HTTP_400_BAD_REQUEST)

        membership = user.memberships.filter(is_active=True).select_related('organization').first()
        org_name = membership.organization.name if membership else 'XenStaff'

        return Response({
            'success': True,
            'valid': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'organization_name': org_name,
        })


class SetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.accounts.services import set_employee_password
        user, auth_token = set_employee_password(data['uid'], data['token'], data['password'])

        active_membership = user.memberships.filter(is_active=True).select_related('organization').first()
        active_org_data = None
        if active_membership:
            active_org_data = {
                'id': str(active_membership.organization.id),
                'name': active_membership.organization.name,
                'slug': active_membership.organization.slug,
                'role': active_membership.role,
                'onboarding_completed': active_membership.organization.onboarding_completed,
            }

        return Response({
            'success': True,
            'message': 'Password set successfully! Your account is now active.',
            'token': auth_token.key,
            'user': UserSerializer(user).data,
            'active_organization': active_org_data,
        }, status=status.HTTP_200_OK)
