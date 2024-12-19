import enum


class PermissionEnum(enum.Enum):
    PROJECT_VIEW = 10
    REPO_READ = 0
    REPO_WRITE = 1
    REPO_ADMIN = 8
    PROJECT_READ = 2
    PROJECT_WRITE = 3
    PROJECT_ADMIN = 4
    LICENSED_USER = 9
    PROJECT_CREATE = 5
    ADMIN = 6
    SYS_ADMIN = 7
    NO_ACCESS = 11
