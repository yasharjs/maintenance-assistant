/* eslint-disable object-curly-spacing */
/* eslint-disable indent */
/* eslint-disable react/jsx-indent */
import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport } from "../../components/ui/toast";
import { useToast } from "../../hooks/use-toast";
export function Toaster() {
  const {toasts} = useToast();
  return (
    <ToastProvider duration={3000}>
    {toasts.map(function ({ id, title, description, action, ...props }) {
        return (
          <Toast key={id} {...props}>
            {title && <ToastTitle>{title}</ToastTitle>}
            {description && <ToastDescription>{description}</ToastDescription>}
            {action}
            <ToastClose />
          </Toast>
        );
      })}
    <ToastViewport />
  </ToastProvider>
  );
}
