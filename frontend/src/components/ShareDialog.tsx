import React, { useState } from "react";
import { Check, Copy, Globe, Lock, Share } from "lucide-react";

import { Button } from "../components/ui/button";
import { Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { useToast } from "../hooks/use-toast";

interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  chatId: string;
  chatTitle: string;
}

const ShareDialog: React.FC<ShareDialogProps> = ({
  isOpen,
  onClose,
  chatId,
  chatTitle
}) => {
  const [isPublic, setIsPublic] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const shareUrl = `${window.location.origin}/chat/${chatId}`;

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast({
        title: "Link copied!",
        description: "The share link has been copied to your clipboard."
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Please copy the link manually.",
        variant: "destructive"
      });
    }
  };

  const togglePublicAccess = () => {
    setIsPublic(!isPublic);
    toast({
      title: isPublic ? "Chat made private" : "Chat made public",
      description: isPublic
        ? "Only you can access this chat now."
        : "Anyone with the link can now view this chat."
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Share className="w-5 h-5 mr-2" />
            Share Chat
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          <div>
            <h3 className="font-medium text-sm mb-2">{chatTitle}</h3>
            <p className="text-sm text-muted-foreground">
              Share this conversation with others through a public link.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-3">
                {isPublic ? (
                  <Globe className="w-5 h-5 text-primary" />
                ) : (
                  <Lock className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium text-sm">
                    {isPublic ? "Public access" : "Private access"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {isPublic
                      ? "Anyone with the link can view"
                      : "Only you can access this chat"}
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={togglePublicAccess}>
                {isPublic ? "Make Private" : "Make Public"}
              </Button>
            </div>

            {isPublic && (
              <div className="space-y-2">
                <Label htmlFor="share-link">Share link</Label>
                <div className="flex space-x-2">
                  <Input
                    id="share-link"
                    value={shareUrl}
                    readOnly
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={copyToClipboard}
                    className="shrink-0"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-primary" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Messages you send after creating the share link won't be
                  shared.
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ShareDialog;
