import traceback
from pytz import UTC
from datetime import datetime, timedelta

from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear, TruncWeek, TruncQuarter

from api.models import Expense, ExpenseUser

from rest_framework.views import APIView
from rest_framework.response import Response

from common.utils import verify_expense_date_format

from django.conf import settings


class ExpenseView(APIView):

    authentication_classes = []

    def get(self, request):
        try:
            query_params = dict(request.GET)
            user_id = query_params.get('user_id')[0]
            user = ExpenseUser.objects.get(user_id=user_id)
            if not user:
                return Response({'message': 'Invalid user!'}, status=404)
            data = Expense.objects.all().filter(user=user).values()
            return Response({'data': data}, status=200)
        except Exception as e:
            print(e)
            return Response({'message': 'Some unexpected error occured!'}, status=500)

    def post(self, request):
        try:
            request_data = dict(request.data)
            amount = request_data.get('amount')
            category = request_data.get('category')
            desc = request_data.get('description', '')
            expense_date = request_data.get('expense_date')
            user_id = request_data.get('user_id')
            user = ExpenseUser.objects.get(user_id=user_id)
            source = request_data.get('source')
            message_id = request_data.get('message_id')

            if not user:
                return Response({'message': 'User not found!'}, status=404)
            if not amount or not category:
                return Response({'message': 'Amount or Category must be specified!'}, status=400)
            if expense_date:
                if not verify_expense_date_format(expense_date):
                    return Response({'message': 'Expense data is wrong format. Please enter date in dd-mm-yyyy format.'}, status=400)
                expense_date = datetime.strptime(expense_date, '%d-%m-%Y')
            else:
                expense_date = datetime.utcnow().date().strftime('%d-%m-%Y')

            expense = Expense(amount=amount, category=category, description=desc, expense_date=expense_date.date(),
                              user=user, updated_at=datetime.utcnow(), source=source, unique_message_id=message_id)
            expense.save()

            return Response({'message': 'Expense added'}, status=201)
        except Exception as e:
            print(traceback.print_exc())
            return Response({'message': 'Some unexpected error occured!'}, status=500)

    def patch(self, request):
        try:
            request_data = dict(request.data)
            amount = request_data.get('amount')
            category = request_data.get('category')
            desc = request_data.get('description', '')
            expense_date = request_data.get('expense_date')
            user_id = request_data.get('user_id')
            user = ExpenseUser.objects.get(user_id=user_id)
            message_id = request_data.get('message_id')

            expense = Expense.objects.get(unique_message_id=message_id)
            if not expense:
                return Response({'message': 'No expense mapped to given to message id.'}, status=404)

            if amount:
                expense.amount = amount
            if category:
                expense.category = category
            if desc:
                expense.description = desc
            if expense_date:
                expense.expense_date = expense_date

            expense.save()
            return Response({'message': 'Expense updated!'}, status=201)
        except Exception as e:
            print(e)
            return Response({'message': 'Some unexpected error occured!'}, status=500)

    def delete(self, request):
        try:
            request_data = dict(request.data)
            user_id = request_data.get('user_id')
            message_id = request_data.get('message_id')

            if not message_id:
                return Response({'message': 'Unable to delete expense, message id is null'}, status=404)

            expense = Expense.objects.all().filter(unique_message_id=message_id)
            if not expense:
                return Response({'message': 'No expense mapped to given to message id.'}, status=404)
            expense.delete()

            return Response({'message': 'Expense deleted'}, status=200)
        except Exception as e:
            print(e)
            return Response({'message': 'Some unexpected error occured!'}, status=500)


class SummaryView(APIView):

    def get(self, request):
        try:
            query_params = dict(request.query_params)
            print(query_params)
            start_date_str = query_params.get('start_date')[0]
            end_date_str = query_params.get('end_date')[0]
            user_id = query_params.get('user_id')[0]
            if not start_date_str or not end_date_str:
                return Response({'message': 'Start date or end date can not be null.'}, status=400)
            user = ExpenseUser.objects.get(user_id=user_id)
            if not user:
                return Response({'message': 'User not found!'}, status=404)
            start_date = datetime.strptime(
                start_date_str, settings.DATE_TIME_FORMATTER).astimezone(tz=UTC)
            end_date = datetime.strptime(end_date_str, settings.DATE_TIME_FORMATTER).astimezone(
                tz=UTC) + timedelta(hours=23, minutes=59)
            expenses = Expense.objects.all().filter(user=user).filter(expense_date__gte=start_date).filter(
                expense_date__lte=end_date).order_by('-expense_date').values('amount', 'description', 'category', 'expense_date')
            # TODO Trigger telegram message
            return Response(data=expenses, status=200)
        except Exception as e:
            print(f'Exception occured in function_name. Error: {e}')
            return Response({'message': 'Some unexpected error occured!'}, status=500)


class AnalysisView(APIView):

    def get(self, request):
        try:
            query_params = dict(request.query_params)
            print(query_params)
            start_date_str = query_params.get('start_date')[0]
            end_date_str = query_params.get('end_date')[0]
            user_id = query_params.get('user_id')[0]
            chart_type = query_params.get('chart_type')[0]
            if not start_date_str or not end_date_str:
                return Response({'message': 'Start date or end date can not be null.'}, status=400)
            user = ExpenseUser.objects.get(user_id=user_id)
            if not user:
                return Response({'message': 'User not found!'}, status=404)
            start_date = datetime.strptime(
                start_date_str, settings.DATE_TIME_FORMATTER).astimezone(tz=UTC)
            end_date = datetime.strptime(end_date_str, settings.DATE_TIME_FORMATTER).astimezone(
                tz=UTC) + timedelta(hours=23, minutes=59)
            expenses = Expense.objects.all().values('category').values('category').order_by('category').annotate(total_amount=Sum('amount'))
            categories = []
            expense_amount = []
            for item in expenses:
                categories.append(item['category'])
                expense_amount.append(float(item['total_amount']))
            return Response(data=expenses, status=200)
        except Exception as e:
            print(f'Exception occured in function_name. Error: {e}')
            return Response({'message': 'Some unexpected error occured!'}, status=500)


class TrendsView(APIView):

    def get(self, request):
        try:
            query_params = dict(request.query_params)
            user_id = query_params.get('user_id')[0]
            trend_type = query_params.get('trend_type')[0]
            user = ExpenseUser.objects.get(user_id=user_id)
            if not user:
                return Response({'message': 'User not found!'}, status=404)

            if trend_type == "weekly":
                expenses = Expense.objects.all().annotate(week=TruncWeek('expense_date')).values('week').annotate(total_amount=Sum('amount')).order_by('week')
            elif trend_type == "monthly":
                expenses = Expense.objects.all().annotate(month=TruncMonth('expense_date')).values('month').annotate(total_amount=Sum('amount')).order_by('month')
            elif trend_type == "quarterly":
                expenses = Expense.objects.all().annotate(quarter=TruncQuarter('expense_date')).values('quarter').annotate(total_amount=Sum('amount')).order_by('quarter')
            else:
                expenses = Expense.objects.all().annotate(year=TruncYear('expense_date')).values('year').annotate(total_amount=Sum('amount')).order_by('year')   

            duration = []
            expense_amount = []
            for item in expenses:                
                duration.append(item['month'].strftime('%b %Y'))
                expense_amount.append(float(item['total_amount']))
            
            print(duration, expense_amount)

            return Response(data=expenses, status=200)
        except Exception as e:
            print(f'Exception occured in function_name. Error: {e}')
            return Response({'message': 'Some unexpected error occured!'}, status=500)
