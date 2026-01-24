"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Plus, Users, CheckCircle, Clock, Copy, Trash2, Link, Key } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface Client {
  id: number;
  client_id: string | null;
  email: string;
  username: string | null;
  onboarding_completed: boolean;
  onboarding_step: number;
  company_name: string | null;
  is_active: boolean;
  created_at: string;
}

interface AccessToken {
  id: number;
  token: string;
  token_preview: string;
  url: string;
  label: string | null;
  expires_at: string;
  is_read_only: boolean;
  status: "active" | "used" | "expired" | "revoked";
  created_at: string;
  used_at: string | null;
  used_by_ip: string | null;
}

interface CreateAccessTokenResponse {
  id: number;
  token: string;
  url: string;
  label: string | null;
  expires_at: string;
  is_read_only: boolean;
  status: string;
  created_at: string;
}

export default function ClientsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newClient, setNewClient] = useState({
    username: "",
    password: "",
  });
  const [createdCredentials, setCreatedCredentials] = useState<{
    client_id: string;
    password: string;
  } | null>(null);
  const [clientToDelete, setClientToDelete] = useState<Client | null>(null);

  // Access token state
  const [isTokenDialogOpen, setIsTokenDialogOpen] = useState(false);
  const [newTokenLabel, setNewTokenLabel] = useState("");
  const [newTokenExpiry, setNewTokenExpiry] = useState("24");
  const [createdToken, setCreatedToken] = useState<CreateAccessTokenResponse | null>(null);
  const [tokenToRevoke, setTokenToRevoke] = useState<AccessToken | null>(null);

  // Admin-only route guard
  useEffect(() => {
    if (!authLoading && user && !user.is_superuser) {
      router.push("/dashboard");
    }
  }, [authLoading, user, router]);

  const { data: clients, isLoading } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: async () => {
      const response = await api.get("/api/v1/admin/clients");
      return response.data;
    },
    enabled: !!user?.is_superuser, // Only fetch if user is admin
  });

  const { data: accessTokens, isLoading: tokensLoading } = useQuery<AccessToken[]>({
    queryKey: ["access-tokens"],
    queryFn: async () => {
      const response = await api.get("/api/v1/admin/access-tokens");
      return response.data;
    },
    enabled: !!user?.is_superuser,
  });

  const createClient = useMutation({
    mutationFn: async (data: { username: string; password: string }) => {
      const response = await api.post("/api/v1/admin/clients", data);
      return response.data as Client;
    },
    onSuccess: (data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
      setCreatedCredentials({
        client_id: data.client_id ?? "",
        password: variables.password,
      });
      setNewClient({ username: "", password: "" });
      toast.success("Client created successfully!");
    },
    onError: (error: Error) => {
      toast.error(error.message ?? "Failed to create client");
    },
  });

  const deleteClient = useMutation({
    mutationFn: async (clientId: number) => {
      await api.delete(`/api/v1/admin/clients/${clientId}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["clients"] });
      setClientToDelete(null);
      toast.success("Client deleted successfully!");
    },
    onError: (error: Error) => {
      toast.error(error.message ?? "Failed to delete client");
    },
  });

  const createAccessToken = useMutation({
    mutationFn: async (data: { label: string; expires_in_hours: number }) => {
      const response = await api.post("/api/v1/admin/access-tokens", data);
      return response.data as CreateAccessTokenResponse;
    },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ["access-tokens"] });
      setCreatedToken(data);
      setNewTokenLabel("");
      setNewTokenExpiry("24");
      toast.success("Access link created successfully!");
    },
    onError: (error: Error) => {
      toast.error(error.message ?? "Failed to create access link");
    },
  });

  const revokeAccessToken = useMutation({
    mutationFn: async (tokenId: number) => {
      await api.delete(`/api/v1/admin/access-tokens/${tokenId}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["access-tokens"] });
      setTokenToRevoke(null);
      toast.success("Access link revoked!");
    },
    onError: (error: Error) => {
      toast.error(error.message ?? "Failed to revoke access link");
    },
  });

  // Show loading while checking auth or if not admin
  if (authLoading || !user?.is_superuser) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const handleDeleteClient = () => {
    if (clientToDelete) {
      deleteClient.mutate(clientToDelete.id);
    }
  };

  const handleCreateClient = (e: React.FormEvent) => {
    e.preventDefault();
    createClient.mutate(newClient);
  };

  const generatePassword = () => {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%";
    let password = "";
    for (let i = 0; i < 12; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setNewClient({ ...newClient, password });
  };

  const copyCredentials = () => {
    if (createdCredentials) {
      const text = `Client ID: ${createdCredentials.client_id}\nPassword: ${createdCredentials.password}`;
      void navigator.clipboard.writeText(text);
      toast.success("Credentials copied to clipboard!");
    }
  };

  const handleCreateAccessToken = (e: React.FormEvent) => {
    e.preventDefault();
    createAccessToken.mutate({
      label: newTokenLabel || undefined,
      expires_in_hours: parseInt(newTokenExpiry, 10),
    } as { label: string; expires_in_hours: number });
  };

  const handleRevokeToken = () => {
    if (tokenToRevoke) {
      revokeAccessToken.mutate(tokenToRevoke.id);
    }
  };

  const copyAccessUrl = (url: string) => {
    void navigator.clipboard.writeText(url);
    toast.success("Access link copied to clipboard!");
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-emerald-500/20 text-emerald-500">Active</Badge>;
      case "used":
        return <Badge className="bg-blue-500/20 text-blue-500">Used</Badge>;
      case "expired":
        return <Badge className="bg-gray-500/20 text-gray-500">Expired</Badge>;
      case "revoked":
        return <Badge className="bg-red-500/20 text-red-500">Revoked</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Admin</h1>
        <p className="text-muted-foreground">
          Manage clients and access links
        </p>
      </div>

      <Tabs defaultValue="clients" className="space-y-6">
        <TabsList>
          <TabsTrigger value="clients" className="gap-2">
            <Users className="h-4 w-4" />
            Clients
          </TabsTrigger>
          <TabsTrigger value="access-tokens" className="gap-2">
            <Key className="h-4 w-4" />
            Access Links
          </TabsTrigger>
        </TabsList>

        <TabsContent value="clients" className="space-y-6">
          <div className="flex items-center justify-end">
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Add Client
            </Button>
          </DialogTrigger>
          <DialogContent>
            {createdCredentials ? (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-emerald-500">
                    <CheckCircle className="h-5 w-5" />
                    Client Created!
                  </DialogTitle>
                  <DialogDescription>
                    Share these credentials with your client. They will complete
                    onboarding on first login.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 rounded-lg border border-white/10 bg-white/[0.02] p-4">
                  <div>
                    <Label className="text-xs text-muted-foreground">Client ID</Label>
                    <p className="font-mono text-lg font-semibold">{createdCredentials.client_id}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">
                      Temporary Password
                    </Label>
                    <p className="font-mono text-sm">{createdCredentials.password}</p>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={copyCredentials} className="gap-2">
                    <Copy className="h-4 w-4" />
                    Copy Credentials
                  </Button>
                  <Button
                    onClick={() => {
                      setCreatedCredentials(null);
                      setIsDialogOpen(false);
                    }}
                  >
                    Done
                  </Button>
                </DialogFooter>
              </>
            ) : (
              <>
                <DialogHeader>
                  <DialogTitle>Add New Client</DialogTitle>
                  <DialogDescription>
                    Create a new client account. They will complete onboarding when
                    they first log in.
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateClient} className="space-y-4">
                  <div className="rounded-lg border border-dashed border-white/20 bg-white/[0.02] p-3">
                    <p className="text-xs text-muted-foreground">
                      A unique Client ID (e.g., SV-A1B2C3) will be auto-generated for login
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">Client Name</Label>
                    <Input
                      id="username"
                      placeholder="John Smith"
                      value={newClient.username}
                      onChange={(e) =>
                        setNewClient({ ...newClient, username: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="password">Temporary Password *</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={generatePassword}
                      >
                        Generate
                      </Button>
                    </div>
                    <Input
                      id="password"
                      type="text"
                      placeholder="Enter or generate password"
                      value={newClient.password}
                      onChange={(e) =>
                        setNewClient({ ...newClient, password: e.target.value })
                      }
                      required
                      minLength={8}
                    />
                  </div>
                  <DialogFooter>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createClient.isPending}>
                      {createClient.isPending && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      Create Client
                    </Button>
                  </DialogFooter>
                </form>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            All Clients
          </CardTitle>
          <CardDescription>
            View and manage all client accounts
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : clients && clients.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Onboarding</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clients.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell>
                      <code className="rounded bg-muted px-2 py-1 font-mono text-sm font-semibold">
                        {client.client_id ?? "—"}
                      </code>
                    </TableCell>
                    <TableCell>
                      <p className="font-medium">{client.username ?? "—"}</p>
                    </TableCell>
                    <TableCell>{client.company_name ?? "—"}</TableCell>
                    <TableCell>
                      <Badge
                        variant={client.is_active ? "default" : "secondary"}
                      >
                        {client.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {client.onboarding_completed ? (
                        <Badge
                          variant="outline"
                          className="border-emerald-500/50 text-emerald-500"
                        >
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Complete
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className="border-amber-500/50 text-amber-500"
                        >
                          <Clock className="mr-1 h-3 w-3" />
                          Step {client.onboarding_step}/5
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(client.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={() => setClientToDelete(client)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Users className="mb-4 h-12 w-12 text-muted-foreground/50" />
              <h3 className="mb-2 text-lg font-medium">No clients yet</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Create your first client to get started
              </p>
              <Button onClick={() => setIsDialogOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Add Client
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="access-tokens" className="space-y-6">
          <div className="flex items-center justify-end">
            <Dialog open={isTokenDialogOpen} onOpenChange={setIsTokenDialogOpen}>
              <DialogTrigger asChild>
                <Button className="gap-2">
                  <Link className="h-4 w-4" />
                  Generate Access Link
                </Button>
              </DialogTrigger>
              <DialogContent>
                {createdToken ? (
                  <>
                    <DialogHeader>
                      <DialogTitle className="flex items-center gap-2 text-emerald-500">
                        <CheckCircle className="h-5 w-5" />
                        Access Link Created!
                      </DialogTitle>
                      <DialogDescription>
                        Share this link with your reviewer. It can only be used once.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 rounded-lg border border-white/10 bg-white/[0.02] p-4">
                      <div>
                        <Label className="text-xs text-muted-foreground">Access URL</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm break-all">
                            {createdToken.url}
                          </code>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => copyAccessUrl(createdToken.url)}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <Label className="text-xs text-muted-foreground">Expires</Label>
                          <p>{new Date(createdToken.expires_at).toLocaleString()}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Access Type</Label>
                          <p>{createdToken.is_read_only ? "Read-only" : "Full access"}</p>
                        </div>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => copyAccessUrl(createdToken.url)} className="gap-2">
                        <Copy className="h-4 w-4" />
                        Copy Link
                      </Button>
                      <Button
                        onClick={() => {
                          setCreatedToken(null);
                          setIsTokenDialogOpen(false);
                        }}
                      >
                        Done
                      </Button>
                    </DialogFooter>
                  </>
                ) : (
                  <>
                    <DialogHeader>
                      <DialogTitle>Generate Access Link</DialogTitle>
                      <DialogDescription>
                        Create a one-time access link for superior review. The link expires
                        after the specified time and can only be used once.
                      </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleCreateAccessToken} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="token-label">Label (optional)</Label>
                        <Input
                          id="token-label"
                          placeholder="e.g., CEO Review"
                          value={newTokenLabel}
                          onChange={(e) => setNewTokenLabel(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="token-expiry">Expires In</Label>
                        <select
                          id="token-expiry"
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          value={newTokenExpiry}
                          onChange={(e) => setNewTokenExpiry(e.target.value)}
                        >
                          <option value="1">1 hour</option>
                          <option value="6">6 hours</option>
                          <option value="12">12 hours</option>
                          <option value="24">24 hours (recommended)</option>
                          <option value="48">48 hours</option>
                          <option value="72">72 hours (maximum)</option>
                        </select>
                      </div>
                      <div className="rounded-lg border border-dashed border-white/20 bg-white/[0.02] p-3">
                        <p className="text-xs text-muted-foreground">
                          Access links grant read-only admin access to the dashboard.
                          The reviewer will see everything an admin sees but cannot make changes.
                        </p>
                      </div>
                      <DialogFooter>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setIsTokenDialogOpen(false)}
                        >
                          Cancel
                        </Button>
                        <Button type="submit" disabled={createAccessToken.isPending}>
                          {createAccessToken.isPending && (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          )}
                          Generate Link
                        </Button>
                      </DialogFooter>
                    </form>
                  </>
                )}
              </DialogContent>
            </Dialog>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Access Links
              </CardTitle>
              <CardDescription>
                One-time access links for secure dashboard review
              </CardDescription>
            </CardHeader>
            <CardContent>
              {tokensLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : accessTokens && accessTokens.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Token</TableHead>
                      <TableHead>Label</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead>Used</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {accessTokens.map((token) => (
                      <TableRow key={token.id}>
                        <TableCell>
                          <code className="rounded bg-muted px-2 py-1 font-mono text-xs">
                            {token.token_preview}
                          </code>
                        </TableCell>
                        <TableCell>{token.label ?? "—"}</TableCell>
                        <TableCell>{getStatusBadge(token.status)}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(token.expires_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm">
                          {token.used_at ? (
                            <span className="text-muted-foreground">
                              {new Date(token.used_at).toLocaleString()}
                              {token.used_by_ip && (
                                <span className="block text-xs">from {token.used_by_ip}</span>
                              )}
                            </span>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell>
                          {token.status === "active" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive"
                              onClick={() => setTokenToRevoke(token)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Key className="mb-4 h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mb-2 text-lg font-medium">No access links yet</h3>
                  <p className="mb-4 text-sm text-muted-foreground">
                    Generate a one-time link to share dashboard access
                  </p>
                  <Button onClick={() => setIsTokenDialogOpen(true)} className="gap-2">
                    <Link className="h-4 w-4" />
                    Generate Access Link
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!clientToDelete} onOpenChange={(open) => !open && setClientToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Client</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete{" "}
              <span className="font-semibold">{clientToDelete?.username ?? clientToDelete?.client_id}</span>?
              This action cannot be undone and will permanently remove their account and all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteClient}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteClient.isPending}
            >
              {deleteClient.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Revoke Token Confirmation Dialog */}
      <AlertDialog open={!!tokenToRevoke} onOpenChange={(open) => !open && setTokenToRevoke(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke Access Link</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to revoke this access link
              {tokenToRevoke?.label && (
                <span className="font-semibold"> ({tokenToRevoke.label})</span>
              )}
              ? The link will no longer work even if it hasn&apos;t been used.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRevokeToken}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={revokeAccessToken.isPending}
            >
              {revokeAccessToken.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
