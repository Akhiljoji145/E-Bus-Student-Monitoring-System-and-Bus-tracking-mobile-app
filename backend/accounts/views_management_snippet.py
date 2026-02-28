
class UpdateMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if not (request.user.is_management or request.user.is_superuser):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = User.objects.get(pk=pk)

            # Authorization Check
            if not request.user.is_superuser:
                if user.managed_by != request.user:
                     return Response({'error': 'You do not have permission to update this user.'}, status=status.HTTP_403_FORBIDDEN)

            data = request.data
            
            # Common Fields
            if 'username' in data: user.username = data['username']
            if 'email' in data: user.email = data['email']
            # if 'phone' in data: user.phone = data['phone'] # Assuming phone is in User model or Profile

            # Teacher Fields
            if user.is_teacher:
                if 'class_in_charge' in data:
                    try:
                        user.class_in_charge = Grade.objects.get(id=data['class_in_charge']) if data['class_in_charge'] else None
                    except Grade.DoesNotExist:
                        pass
                if 'bus' in data:
                    try:
                        user.bus = Bus.objects.get(id=data['bus']) if data['bus'] else None
                    except Bus.DoesNotExist:
                        pass

            # Student/Parent Fields
            if user.is_student and user.parent and 'parent_details' in data:
                parent_data = data['parent_details']
                parent = user.parent
                if 'name' in parent_data: parent.username = parent_data['name'] # Using username as name
                if 'email' in parent_data: parent.email = parent_data['email']
                parent.save()

            user.save()
            return Response({'message': 'Member updated successfully'}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
