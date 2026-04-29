type NavigateFn = (path: string, options?: { replace?: boolean }) => void;

let _navigate: NavigateFn | null = null;

export const setNavigator = (fn: NavigateFn): void => {
  _navigate = fn;
};

export const navigate = (path: string, options?: { replace?: boolean }): void => {
  if (_navigate) {
    _navigate(path, options);
  } else {
    window.location.href = path; // fallback before router mounts
  }
};
