from django.http import QueryDict


class RequestDataManipulationsDecorators:
    @staticmethod
    def extract_all_request_data_to_kwargs(function):
        """
        extract data in queryset to kwargs
        """

        def function_to_execute(self, request, *args, **kwargs):
            if request.method.lower() == "get":
                request_data = request.GET
            else:
                request_data = request.data

            for key, value in request_data.items():
                kwargs[key] = value

            return function(self, request, *args, **kwargs)

        function_to_execute.__name__ = function.__name__
        return function_to_execute

    @staticmethod
    def extract_required_data_to_kwargs(function):
        def function_to_execute(self, request, *args, **kwargs):
            required_fields = self.get_required_fields()
            if request.method.lower() == "get":
                request_data = request.GET
            else:
                request_data = request.data

            for field in required_fields:
                kwargs[field] = request_data.get(field)
            return function(self, request, *args, **kwargs)

        function_to_execute.__name__ = function.__name__
        return function_to_execute

    @staticmethod
    def update_request_data_with_owner_data(owner_field_name="owner"):
        def inner(function):
            def function_to_execute(self, request, *args, **kwargs):
                if isinstance(request.data, QueryDict):
                    request.data._mutable = True
                request.data[owner_field_name] = request.user.id
                return function(self, request, *args, **kwargs)

            function_to_execute.__name__ = function.__name__
            return function_to_execute

        return inner

    @staticmethod
    def mutable_request_data(function):
        def function_to_execute(self, request, *args, **kwarg):
            if isinstance(request.data, QueryDict):
                request.data._mutable = True
            return function(self, request, *args, **kwarg)

        function_to_execute.__name__ = function.__name__
        return function_to_execute