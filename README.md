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
apt install python3 python3-venv python-is-python3
```

**Подготовка SSH ключей, для взаимодействия с проектом Github**

1. Сначала необходимо сгенерировать SSH публичный и приватный ключ.
```
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/tsutmb-hostel
```
2. Содержимое публичного ключа `tsutmb-hostel.pub` необходимо установить в проекте **GitHub** в разделе _**Deploy keys**_.
3. В файл `~/.ssh/config` необходимо вписать содержимое:
```
Host github.com-tsutmb-hostel
                Hostname github.com
                IdentityFile=~/.ssh/tsutmb-hostel
```
4. Перейти в директорию, куда будет установлена папка с проектом.
```
cd /srv/
```
5. Клонировать проект.
```
git clone git@github.com-tsutmb-hostel:ArthurKoba/tsutmb-hostel.git
```
6. Зайти в папку с проектом.
```
cd tsutmb-hostel
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
