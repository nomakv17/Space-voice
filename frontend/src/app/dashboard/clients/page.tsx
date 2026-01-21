"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
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
import { Loader2, Plus, Users, CheckCircle, Clock, Copy, Trash2 } from "lucide-react";
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

export default function ClientsPage() {
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

  const { data: clients, isLoading } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: async () => {
      const response = await api.get("/api/v1/admin/clients");
      return response.data;
    },
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
      toast.error(error.message || "Failed to create client");
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
      toast.error(error.message || "Failed to delete client");
    },
  });

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Clients</h1>
          <p className="text-muted-foreground">
            Manage your client accounts and onboarding
          </p>
        </div>
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
    </div>
  );
}
