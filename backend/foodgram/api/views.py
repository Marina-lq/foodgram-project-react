import io
import reportlab
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, api_view
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db.models.aggregates import Count, Sum
from django.db.models.expressions import Exists, OuterRef, Value
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .serializers import (
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    SubscribeRecipeSerializer,
    SubscribeSerializer,
    TagSerializer,
    TokenSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserPasswordSerializer,
)
from djoser.views import UserViewSet
from foodgram.settings import FILENAME
from recipes.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Subscribe,
    Tag,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from users.models import User

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAdminOrReadOnly
from .permissions import IsAuthorOrAdminOrReadOnly

reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + "/data")

pdfmetrics.registerFont(TTFont("arial", "arial.ttf"))


class GetObjectMixin:
    """Удаление/добавление рецептов из избранного/корзины."""

    serializer_class = SubscribeRecipeSerializer
    permission_classes = (AllowAny,)

    def get_object(self):
        recipe_id = self.kwargs["recipe_id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe


class PermissionAndPaginationMixin:
    """Список тегов и ингридиентов."""

    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class AddAndDeleteSubscribe(
    generics.RetrieveDestroyAPIView, generics.ListCreateAPIView
):
    """Подписка и отписка от пользователя."""

    serializer_class = SubscribeSerializer

    def get_queryset(self):
        return (
            self.request.user.follower.select_related("following")
            .prefetch_related("following__recipe")
            .annotate(
                recipes_count=Count("following__recipe"),
                is_subscribed=Value(True),
            )
        )

    def get_object(self):
        user_id = self.kwargs["user_id"]
        user = get_object_or_404(User, id=user_id)
        self.check_object_permissions(self.request, user)
        return user

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.id == instance.id:
            return Response(
                {"errors": "На самого себя не подписаться!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.follower.filter(author=instance).exists():
            return Response(
                {"errors": "Уже подписан!"}, status=status.HTTP_400_BAD_REQUEST
            )
        subs = request.user.follower.create(author=instance)
        serializer = self.get_serializer(subs)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.follower.filter(author=instance).delete()


class AddDeleteFavoriteRecipe(
    GetObjectMixin, generics.RetrieveDestroyAPIView, generics.ListCreateAPIView
):
    """Добавление и удаление рецепта в избранное."""

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        request.user.favorite_recipe.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.favorite_recipe.recipe.remove(instance)


class AddDeleteShoppingCart(
    GetObjectMixin, generics.RetrieveDestroyAPIView, generics.ListCreateAPIView
):
    """Добавление и удаление рецепта из корзины."""

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        request.user.shopping_cart.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.shopping_cart.recipe.remove(instance)


class AuthToken(ObtainAuthToken):
    """Авторизация пользователя."""

    serializer_class = TokenSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"auth_token": token.key},
                        status=status.HTTP_201_CREATED)


class UsersViewSet(UserViewSet):
    """Пользователи."""

    serializer_class = UserListSerializer
    permission_classes = (IsAuthorOrAdminOrReadOnly,)

    def get_queryset(self):
        return (
            User.objects.annotate(
                is_subscribed=Exists(
                    self.request.user.follower.filter(author=OuterRef("id"))
                )
            ).prefetch_related("follower", "following")
            if self.request.user.is_authenticated
            else User.objects.annotate(is_subscribed=Value(False))
        )

    def get_serializer_class(self):
        if self.request.method.lower() == "post":
            return UserCreateSerializer
        return UserListSerializer

    def perform_create(self, serializer):
        password = make_password(self.request.data["password"])
        serializer.save(password=password)

    @action(detail=False, permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Список подписок."""

        user = request.user
        queryset = Subscribe.objects.filter(user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(pages, many=True, context={"request":
                                         request})
        return self.get_paginated_response(serializer.data)


class RecipesViewSet(viewsets.ModelViewSet):
    """Создание новых рецептов"""

    queryset = Recipe.objects.all()
    serializer_class = (RecipeWriteSerializer,)
    filterset_class = RecipeFilter
    http_method_names = [
        "post",
        "patch",
        "get",
        "put",
        "delete",
    ]
    permission_classes = (IsAuthorOrAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def create_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient.get("id"),
                    amount=ingredient.get("amount"),
                )
                for ingredient in ingredients
            ]
        )

    def create(self, request, *args, **kwargs):
        serializer = RecipeWriteSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ingredients = serializer.validated_data.pop("ingredients")
        tags = data.pop("tags")
        recipe = Recipe.objects.create(author=request.user,
                                       **serializer.validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(recipe,
                                ingredients)
        serializer = RecipeReadSerializer(instance=recipe,
                                          context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        data = serializer.validated_data
        ingredients = data.pop("ingredients")
        tags = data.pop("tags", None)
        instance = serializer.save()
        if ingredients:
            instance.ingredients.clear()
            self.create_ingredients(instance, ingredients)
        if tags:
            instance.tags.set(tags)

    def get_queryset(self):

        temp = Recipe.objects.select_related("author").prefetch_related(
            "tags", "ingredients", "recipe", "shopping_cart", "favorite_recipe"
        )

        if self.request.user.is_authenticated:
            return temp.annotate(
                is_favorited=Exists(
                    FavoriteRecipe.objects.filter(
                        user=self.request.user, recipe=OuterRef("id")
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=self.request.user, recipe=OuterRef("id")
                    )
                ),
            )
        return temp.annotate(
            is_in_shopping_cart=Value(False),
            is_favorited=Value(False),
        )

    @staticmethod
    def post_method_for_actions(request, pk, serializers):
        data = {"user": request.user.id, "recipe": pk}
        serializer = serializers(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_method_for_actions(request, pk, model):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        model_obj = get_object_or_404(model, user=user, recipe=recipe)
        model_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=["get"],
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        """Загружаем список с ингредиентами."""

        buffer = io.BytesIO()
        page = canvas.Canvas(buffer)
        pdfmetrics.registerFont(TTFont("arial", "arial.ttf"))
        x_position, y_position = 50, 800
        shopping_cart = (
            request.user.shopping_cart.recipe.values(
                "ingredients__name", "ingredients__measurement_unit"
            )
            .annotate(amount=Sum("recipe__amount"))
            .order_by()
        )

        page.setFont("arial", 14)
        if len(shopping_cart) != 0:
            indent = 20
            page.drawString(x_position, y_position, "Cписок покупок:")
            for index, recipe in enumerate(shopping_cart, start=1):
                page.drawString(
                    x_position,
                    y_position - indent,
                    f'{index}. {recipe["ingredients__name"]} - '
                    f'{recipe["amount"]} '
                    f'{recipe["ingredients__measurement_unit"]}.',
                )
                y_position -= 15
                if y_position <= 50:
                    page.showPage()
                    y_position = 800
            page.save()
            buffer.seek(0)
            return FileResponse(buffer, as_attachment=True, filename=FILENAME)
        page.setFont("arial", 24)
        page.drawString(x_position, y_position, "Cписок покупок пуст!")
        page.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=FILENAME)


class TagsViewSet(PermissionAndPaginationMixin, viewsets.ModelViewSet):
    """Список тэгов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientsViewSet(PermissionAndPaginationMixin, viewsets.ModelViewSet):
    """Список ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter


@api_view(["post"])
def set_password(request):
    """Изменить пароль."""

    serializer = UserPasswordSerializer(data=request.data,
                                        context={"request": request})
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return Response({"message": "Пароль изменен!"},
                        status=status.HTTP_201_CREATED)
    return Response(
        {"error": "Введите верные данные!"}, status=status.HTTP_400_BAD_REQUEST
    )
