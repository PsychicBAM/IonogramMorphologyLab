function iml_save_table(name, T)
if istable(T)
  writetable(T, ['out_' name '.csv']);
else
  csvwrite(['out_' name '.csv'], T);
end
end
