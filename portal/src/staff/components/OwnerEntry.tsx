import { useState } from "react";

import OwnerPicker from "./OwnerPicker";

type Props = {
  onOwner: (ownerId: string) => void;
};

export default function OwnerEntry({ onOwner }: Props) {
  const [ownerId, setOwnerId] = useState("");

  const handleManualChange = (value: string) => {
    setOwnerId(value);
    onOwner(value.trim());
  };

  return (
    <div className="grid items-end gap-2 md:grid-cols-[minmax(260px,1fr)_240px]">
      <OwnerPicker
        onPick={(id) => {
          setOwnerId(id);
          onOwner(id);
        }}
      />
      <label className="grid text-sm">
        <span className="text-slate-600">Owner ID</span>
        <input
          className="border rounded px-3 py-2"
          placeholder="Paste owner UUID"
          value={ownerId}
          onChange={(event) => handleManualChange(event.target.value)}
        />
      </label>
    </div>
  );
}
