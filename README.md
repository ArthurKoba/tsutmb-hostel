## Описание

**Управление базой общежития**

---

## Установка и запуск

**Подготовка системы**
1. Обновление репозиториев пакетов и обновление системы.
```
apt update && apt upgrade -y
```
2. Установка необходимых библиотек.
```
apit install python3 python3-venv python-is-python3
```

**Подготовка SSH ключей, для взаимодействия с проектом Github**

1. Сначала необходимо сгенерировать SSH публичный и приватный ключ.
```
ssh-keygen -t rsa -b 4096 -C "email@example.com" -f ~/.ssh/tsutmb-hostel
```
2. Содержимое публичного ключа `tsutmb-hostel.pub` необходимо установить в проекте **GitHub** в разделе _**Deploy keys**_.
3. В файл `~/.ssh/config` необходимо вписать содержимое:
```
Host github.com
    IdentityFile ~/.ssh/tsutmb-hostel
```
4. Создать папку проекта и переместиться в неё.
```
mkdir tsutmb-hostel && cd tsutmb-hostel
```
5. Инициализировать в папке `git` и установить путь к внешнему проекту.
```
git init && git remote add origin git@github.com:ArthurKoba/tsutmb-hostel.git
```
6. Загрузить в текущую папку содержимое `main` ветки.
```
git pull origin main
```
**Создание виртуального окружения, установка зависимостей, сервиса проекта.**
```
bash install.sh
```

## Настройка конфигурационного файла.
```
nano resources/config.ini
```

## Обновление

```
bash update.sh
```
